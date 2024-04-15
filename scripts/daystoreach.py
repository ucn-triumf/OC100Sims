import ROOT
import histHandler
import math
import scipy.optimize
from array import array
from collections import OrderedDict
import ctypes

hbar = 6.582119569e-16 # eVs
fillsPerCycle = 8 # fills of the cell(s) needed for a full nEDM measurement
tau_Xe =  6566.92
tau_Hg = 15271.9

# default experiment parameters. Each of these can be varied within a study by adding specific values to the studyList
defaultParameters = {
  'degaussingTime':        1800., # time needed to degauss the magnetically shielded room (s)
  'cyclesToDegauss':       10, # magnetically shielded room is degaussed after this many cycles
  'stableHours':           16.14, # quiet hours per day that can be used for measurement (h)
  'polarityTime':          150., # time needed to flip electric field polarity (s)
  'polarityFlipsPerCycle': 2, # number of electric field polarity flips per cycle
  'EField':                12500., # electric field (V/cm)
  'detEff':                0.9, # detector quantum efficiency
  'tWait':                 2., # wait time after cell valve is close before spin flip is applied (s)
  'tPulse':                2., # duration of spin flip pulse (s)
  'maxDutyCycle':          0.5, # penalize proton-beam duty cycles above this value in the optimization
  'T2star':                9999., # this gets added onto the polarization lifetime in addition to wall depolarization: 1/T2 = 1/T1 + 1/T2star
  'UCNproduction':         1.4e7, # UCN production rate in source (1/s)
  'sensitivityGoal':       1e-27, # nEDM sensitivity goal (e cm)
  'cells':                 'bottom' # select which cells to use for measurement, 'both', 'top', or 'bottom'
}

# valveClosedTime: duration of irradiation while IV1 is closed
# fillTime: durattion of irradiation while IV1 is open (filling of cell)
# storageTime: duration of ramsey cycle
# emptyingTime: duration of collecting


# calculate polarization from number of low- and high-field seekers
def alpha(Nhfs, Nlfs):
  return (Nhfs - Nlfs)/(Nhfs + Nlfs)

# calculate days needed to reach sensitivity goal
def daysToReach(histograms, valveClosedTime, fillTime, storageTime, emptyingTime, runParameters):
  tEDM = storageTime - runParameters['tWait'] - 2.*runParameters['tPulse']
  spectra = {'source': histHandler.startingSpectrum(histograms, valveClosedTime, fillTime, runParameters['UCNproduction'])}
  results = OrderedDict()

  for cell in ['bottom']:
    for spin in ['hfs', 'lfs']:
      cell_spin_filled = cell + '_' + spin + '_filled'
      spectra[cell_spin_filled] = histHandler.fillingSpectrum(histograms, cell, spin, valveClosedTime, fillTime, runParameters['UCNproduction'])
      dN = ctypes.c_double(0.)
      results['N_' + cell_spin_filled] = spectra[cell_spin_filled].IntegralAndError(0, -1, dN)
      results['dN_' + cell_spin_filled] = dN.value
    Nfilled = results['N_' + cell + '_hfs_filled'] + results['N_' + cell + '_lfs_filled']
    results['alpha_' + cell + '_filled'] = alpha(results['N_' + cell + '_hfs_filled'], results['N_' + cell + '_lfs_filled'])

    for spin in ['hfs', 'lfs']:
      cell_spin_survived = cell + '_' + spin + '_survived'
      spectra[cell_spin_survived] = histHandler.survivingSpectrum(histograms, cell, spin, valveClosedTime, fillTime, storageTime,
                                                                  runParameters['UCNproduction'], runParameters['T2star'])
      dN = ctypes.c_double(0.)
      results['N_' + cell_spin_survived] = spectra[cell_spin_survived].IntegralAndError(0, -1, dN)
      results['dN_' + cell_spin_survived] = dN.value
    Nsurvived = results['N_' + cell + '_hfs_survived'] + results['N_' + cell + '_lfs_survived']
    results['alpha_' + cell + '_survived'] = alpha(results['N_' + cell + '_hfs_survived'], results['N_' + cell + '_lfs_survived'])
    results['lifetime_' + cell] = -storageTime/math.log(Nsurvived/Nfilled)
    results['T2_' + cell] = -storageTime/math.log(results['alpha_' + cell + '_survived']/results['alpha_' + cell + '_filled'])

    for det in ['hfs', 'lfs']:
      cell_det_detected = cell + '_' + det + '_detected'
      spectra[cell_det_detected] = histHandler.emptyingSpectrum(histograms, cell, det, valveClosedTime, fillTime, storageTime, emptyingTime, runParameters['UCNproduction'], runParameters['T2star'])
      
## calculate total counts in each det (8)
      for spin in ['hfs', 'lfs']:
        spectra[cell_det_detected + spin] = histHandler.emptyingSpectrumPolarized(histograms, cell, det, spin, valveClosedTime, fillTime, storageTime, emptyingTime, runParameters['UCNproduction'], runParameters['T2star'])
        dN = ctypes.c_double(0.)
        results['N_' + cell_det_detected + spin] = runParameters['detEff'] * (spectra[cell_det_detected + spin ].IntegralAndError(0, -1, dN))
        results['dN_' + cell_det_detected + spin] = runParameters['detEff'] * dN.value

## Number of counts in each detector
    results['N_' + cell + '_hfs_detected'] = results['N_' + cell + "_hfs_detected" +"hfs"] +  results['N_' + cell + "_hfs_detected"  + "lfs"]
    results['N_' + cell + '_lfs_detected'] = results['N_' + cell + "_lfs_detected" +"hfs"] +  results['N_' + cell + "_lfs_detected"  + "lfs"]
    results['centerofmass_' + cell_det_detected], results['dcenterofmass_' + cell_det_detected], results['zVariance_' + cell_det_detected], results['dzVariance_' + cell_det_detected] =   histHandler.centerOfMass(histograms, cell, det, valveClosedTime, fillTime, storageTime, emptyingTime, runParameters['UCNproduction'], runParameters['T2star'])

## calculate total detected by combining both spins in each detector (1)   
    Ndetected = results['N_' + cell + '_hfs_detected'] + results['N_' + cell + '_lfs_detected']
    results['alpha_' + cell + '_detected'] = alpha(results['N_' + cell + '_hfs_detected'], results['N_' + cell + '_lfs_detected'])
    dN = math.sqrt(results['dN_' + cell + '_hfs_detectedhfs']**2 + results['dN_' + cell + '_hfs_detectedlfs']**2 + results['dN_' + cell + '_lfs_detectedhfs']**2 + results['dN_' + cell + '_lfs_detectedlfs']**2)
    results['dalpha_' + cell + '_detected'] = math.sqrt(dN**2/(results['N_' + cell + '_hfs_detected'] - results['N_' + cell + '_lfs_detected'])**2 + dN**2/Ndetected**2) * results['alpha_' + cell + '_detected']
    
    results['sensitivity_' + cell] = hbar/(2. * tEDM * runParameters['EField'] * math.sqrt(Ndetected) * results['alpha_' + cell + '_detected'])
    results['dsensitivity_' + cell] = math.sqrt((0.5*dN/Ndetected)**2 + (results['dalpha_' + cell + '_detected']/results['alpha_' + cell + '_detected'])**2) * results['sensitivity_' + cell]
        
#    print('{0} cell: filled {1:.0f} +/- {2:.0f} hfs, {3:.0f} +/- {4:.0f} lfs (alpha {5:.3f}); survivors {6:.0f} +/- {7:.0f} hfs, {8:.0f} +/- {9:.0f} lfs (alpha {10:.3f}, T2 {11:.0f} s); detected {12:.0f} +/- {13:.0f} hfs, {14:.0f} +/- {15:.0f} lfs (alpha {16:.3f}); sensitivity {17:.3g} +/- {18:.2g}'.format(\
#           cell, filled['Nhfs'], filled['dNhfs'], filled['Nlfs'], filled['dNlfs'], filled['alpha'], survived['Nhfs'], survived['dNhfs'], survived['Nlfs'], survived['dNlfs'], survived['alpha'], T2, detected['Nhfs'], detected['dNhfs'], detected['Nlfs'], detected['dNlfs'], detected['alpha'], sensitivity[cell], dsensitivity[cell]))
    

  if runParameters['cells'] == 'both':
    cells = ['top', 'bottom']
  else:
    cells = [runParameters['cells']]

  results['sensitivityPerFill'] = 1./math.sqrt(sum(results['sensitivity_' + cell]**-2 for cell in cells))
  results['dsensitivityPerFill'] = math.sqrt(sum((results['dsensitivity_' + cell]/results['sensitivity_' + cell]**3)**2 for cell in cells))*results['sensitivityPerFill']**3
  #cycleTime = max(0, valveClosedTime - emptyingTime) + fillTime + storageTime + emptyingTime
  cycleTime = valveClosedTime + fillTime + storageTime + emptyingTime
  results['cyclesPerDay'] = runParameters['stableHours']*3600./(fillsPerCycle*cycleTime + runParameters['polarityFlipsPerCycle']*runParameters['polarityTime'] + runParameters['degaussingTime']/runParameters['cyclesToDegauss'])
  results['cyclesToReach'] = (results['sensitivityPerFill']/math.sqrt(fillsPerCycle)/runParameters['sensitivityGoal'])**2
  #cyclesToReach = (sensitivityPerFill/math.sqrt(fillsPerCycle)/0.7e-27)**2
  results['dcyclesToReach'] = 2.*results['dsensitivityPerFill']/results['sensitivityPerFill']*results['cyclesToReach']
  results['daysToReach'] = results['cyclesToReach']/results['cyclesPerDay']
  results['ddaysToReach'] = results['dcyclesToReach']/results['cyclesPerDay']
  if results['cyclesPerDay']*(valveClosedTime + fillTime)*fillsPerCycle/86400. > runParameters['maxDutyCycle']:
      results['daysToReach'] = results['daysToReach'] + 10000
#  print('Sensitivity per fill: {0:.3g} +/- {1:.2g} ecm; cycles per day: {2:.1f}, cycles to reach: {3:.0f} +/- {4:.0f}; days to reach: {5:.0f} +/- {6:.0f}; cell tau: {7:0.1f} s'\
#        .format(results['sensitivityPerFill'], results['dsensitivityPerFill'], results['cyclesPerDay'], results['cyclesToReach'], results['dcyclesToReach'], results['daysToReach'], results['ddaysToReach'], -storageTime/math.log(Nsurvived/Nfilled)))
 
  return results, spectra


# calculate UCN storage lifetimes in source and whole UCN guide system
def calculateStorageLifetimes(fillingFile,valveClosedTime,fillingTime,cellStorageTime,emptyingTime):
 
  c = ROOT.TCanvas('c', 'c')
  lifetime = fillingFile.Get('lifetime')
  g2= ROOT.TF1("fit","expo",10,100)  #exponential fit to calculate tau
  lifetime.Fit(g2,"RQ")
  sourceTau = -1./g2.GetParameter(1)
  sourceTauError = g2.GetParError(1)/(math.pow(g2.GetParameter(1),2))

  sysLifetime = fillingFile.Get('sysLifetime')
  g3= ROOT.TF1("fit","expo",10,100)  #exponential fit to calculate tau
  sysLifetime.Fit(g3,"RQ")
  if g3.GetParameter(1) != 0:
    sysTau = -1./g3.GetParameter(1)
    sysTauError = g3.GetParError(1)/(math.pow(g3.GetParameter(1),2))
  else:
    sysTau = 0
    sysTauError = 0
  return sourceTau, sourceTauError, sysTau, sysTauError
  

# apply labels to graphs
def labelAndFormatGraph(gr, labels):
  labelOffset = abs(gr.GetXaxis().GetXmax() - gr.GetXaxis().GetXmin())/50.
  for i, label in enumerate(labels):
#    if i % 2 == 0:
    latex = ROOT.TLatex(gr.GetX()[i] - labelOffset, gr.GetY()[i], label)
    latex.SetTextAlign(21)
    latex.SetTextAngle(90)
#    else:
#      latex = ROOT.TLatex(gr.GetX()[i], gr.GetY()[i] - gr.GetErrorYlow(i), label)
#      latex.SetTextAlign(23)
    latex.SetTextSize(0.035)
    latex.SetTextFont(42)
    gr.GetListOfFunctions().Add(latex)
  gr.SetMarkerStyle(20);
  gr.GetXaxis().SetTitleSize(0.05);
  gr.GetXaxis().SetTitleOffset(0.75);
  gr.GetYaxis().SetTitleSize(0.05);
  gr.GetYaxis().SetTitleOffset(0.9);



ROOT.gROOT.SetBatch(1)
ROOT.gErrorIgnoreLevel = ROOT.kError

studyList = [
             {'name': 'polarizationTracking',
              'parameterName': 'Scenario',
              'runs': [
                       {'commit': 'e5ff7a5c781eb01313cf732a4a3b67741e6d434e', 'parameter': 1., 'label': 'Test'},
                      ]
             }
            ]

for study in studyList:
    studyResults = []
    studySpectra = []
    studyTimings = []
    
    dataFile = None
    plotFile = study['name'] + '.pdf'

    for run in study['runs']:
      for p in defaultParameters:
        if p not in run:
          run[p] = defaultParameters[p]

      files = histHandler.fetchFilesFromGit(run['commit'])
      histograms = histHandler.readHistograms(files[0], files[1], files[2], files[3], files[4])
      maxValveClosedTime = 100.
      maxFillTime = min(histograms[h].GetXaxis().GetXmax() for h in histograms if h.startswith('fill')) - maxValveClosedTime
      maxStorageTime = min(histograms[h].GetXaxis().GetXmax() for h in histograms if h.startswith('storage'))
      maxEmptyingTime = min(histograms[h].GetXaxis().GetXmax() for h in histograms if h.startswith(('hfsDetector', 'lfsDetector')))
      print([[0., maxValveClosedTime], [5., maxFillTime], [0., maxStorageTime], [0., maxEmptyingTime]])
      optimized = scipy.optimize.differential_evolution(lambda x: daysToReach(histograms, x[0], x[1], x[2], x[3], run)[0]['daysToReach'],
                                                        [[0., maxValveClosedTime], [5., maxFillTime], [0., maxStorageTime], [0., maxEmptyingTime]], polish=False)
      xmin = optimized.x
      studyTimings.append(xmin)
      nit = optimized.nit
      daysResult, spectra = daysToReach(histograms, xmin[0], xmin[1], xmin[2], xmin[3], run)
      print(run['parameter'], xmin, daysResult, nit)
      print("Optimal days is: ", daysResult['daysToReach'])
     
      storageLifetimes = calculateStorageLifetimes(files[0], xmin[0], xmin[1], xmin[2], xmin[3])
      dutyCycle = daysResult['cyclesPerDay']*(xmin[0] + xmin[1])*fillsPerCycle/86400
      print("Duty cycle: ", dutyCycle)  # cyclesPerDay * beamOnPerCycle/ 24Hr
      print("Source Tau: ", storageLifetimes[0], " +/- ", storageLifetimes[1], " System Tau: " ,storageLifetimes[2], " +/- ", storageLifetimes[3])
      
      if not dataFile:
        dataFile = open(study['name']+'.txt', mode='w')
        for key in sorted(run):
          dataFile.write(key + ',')
        dataFile.write("TimeBeforeValveOpen,FillingTime,CellStorageTime,EmptyingTime,SourceTau,SourceTauError,SystemTau,SystemTauError,DutyCycle")
        for key in daysResult:
          dataFile.write(',' + key)
        dataFile.write('\n')
      for key in sorted(run):
        dataFile.write('{0},'.format(run[key]))
      dataFile.write("{0},{1},{2},{3},{4},{5},{6},{7},{8}".format(xmin[0], xmin[1], xmin[2], xmin[3], storageLifetimes[0], storageLifetimes[1], storageLifetimes[2], storageLifetimes[3], dutyCycle))
      for key in daysResult:
        dataFile.write(',{0}'.format(daysResult[key]))
      dataFile.write('\n')    

      for i, key in enumerate(['sourceLifetime', 'dSourceLifetime', 'systemLifetime', 'dSystemLifetime']):
        daysResult[key] = storageLifetimes[i]
      studyResults.append(daysResult)
      studySpectra.append(spectra)
    

      for f in files:
        f.Close()

    dataFile.close()
    
    studyDays = [studyResult['daysToReach'] for studyResult in studyResults]
    gr = ROOT.TGraphErrors(len(studyDays), array('d', [r['parameter'] for r in study['runs']]), array('d', studyDays),
                           array('d', [0.] * len(studyDays)), array('d', [studyResult['ddaysToReach'] for studyResult in studyResults]))
    gr.SetTitle('{0};{1};Days to reach'.format(study['name'], study['parameterName']))
    labels = [r['label'] for r in study['runs']]
    labelAndFormatGraph(gr, labels)
    p = ROOT.TCanvas('p','p')
    p.cd()
    gr.Draw("AP")
    
    bestDays = min(studyDays)    
    relative = ROOT.TGaxis(gr.GetXaxis().GetXmax(),gr.GetHistogram().GetMinimum(),gr.GetXaxis().GetXmax(),gr.GetHistogram().GetMaximum(),gr.GetHistogram().GetMinimum()/bestDays,gr.GetHistogram().GetMaximum()/bestDays,510,"+")
    relative.SetTitle("Relative to optimum");
    relative.SetTitleSize(0.05)
    relative.SetTitleOffset(1.0)
    relative.SetLabelOffset(0.045)
    relative.SetLabelFont(42)
    relative.SetTitleFont(42)
    relative.SetTitleSize(0.05)
    relative.SetLabelSize(0.035)
    relative.Draw()
    
    p.Print(plotFile + '[')
    p.Print(plotFile)
    
    sourceTaus = [studyResult['sourceLifetime'] for studyResult in studyResults]
    gr = ROOT.TGraphErrors(len(sourceTaus), array('d', [r['parameter'] for r in study['runs']]), array('d', sourceTaus),
                           array('d', [0.] * len(sourceTaus)), array('d', [studyResult['dSourceLifetime'] for studyResult in studyResults]))
    gr.SetTitle('{0};{1};Source lifetime (s)'.format(study['name'], study['parameterName']))
    labelAndFormatGraph(gr, labels)
    gr.Draw('AP')
    p.Print(plotFile)
    
    p = ROOT.TCanvas('p', 'p')
    p.Divide(1, 2)    
    grs = {}
    for pad, cell in enumerate(['top', 'bottom']):
      p.cd(pad + 1)
      cellLifetimes = [studyResult['lifetime_' + cell] for studyResult in studyResults]
      grs[cell] = ROOT.TGraph(len(cellLifetimes), array('d', [r['parameter'] for r in study['runs']]), array('d', cellLifetimes))
      grs[cell].SetTitle('{0} - {1} cell;{2};Storage lifetime (s)'.format(study['name'], cell, study['parameterName']))
      labelAndFormatGraph(grs[cell], labels)
      grs[cell].Draw('AP')
    p.Print(plotFile)

    p = ROOT.TCanvas('p', 'p')
    p.Divide(1, 2)
    mgs = {}
    for pad, cell in enumerate(['top', 'bottom']):
      p.cd(pad + 1)
      mgs[cell] = ROOT.TMultiGraph()
      mgs[cell].SetTitle('{0} - {1} cell;{2};#alpha'.format(study['name'], cell, study['parameterName']))
      for stage in ['filled', 'survived', 'detected']:
        alphas = [studyResult['alpha_' + cell + '_' + stage] for studyResult in studyResults]
        gr = ROOT.TGraph(len(alphas), array('d', [r['parameter'] for r in study['runs']]), array('d', alphas))
        labelAndFormatGraph(gr, ['']*len(alphas))
        mgs[cell].Add(gr)
      mgs[cell].Draw('AP')
    p.Print(plotFile)
    
    p = ROOT.TCanvas('p', 'p')
    p.Divide(2)    
    for spectra, label, times in zip(studySpectra, labels, studyTimings):
      stacks = {}
      hists = {}
      for pad, cell in enumerate(['top', 'bottom']):
        p.cd(pad + 1)
        stacks[cell] = ROOT.THStack()
        hists['source'] = spectra['source'].Clone()
        hists['source'].Scale(0.01)
        hists['source'].SetTitle('Source x0.01')
        stacks[cell].Add(hists['source'])
        for stage, duration in zip(['filled', 'survived', 'detected'], [(int(times[0]), int(times[1])), int(times[2]), int(times[3])]):
          hists[cell + stage] = spectra[cell + '_hfs_' + stage] + spectra[cell + '_lfs_' + stage]
          hists[cell + stage].SetTitle('{0} {1} s'.format(stage, duration))
          stacks[cell].Add(hists[cell + stage])
        stacks[cell].SetTitle('{0} ({1} cell);Total energy (neV);Number of UCN'.format(label, cell))
        stacks[cell].Draw('hist pfc nostack')
        ROOT.gPad.BuildLegend()
      p.Print(plotFile)
    p.Print(plotFile + ']')


