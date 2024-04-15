import ROOT
import subprocess
import ctypes
import math

# fetches result files from given git commit and returns them as a list of ROOT TMemFiles [filling, topStorage, bottomStorage, topEmpty, bottomEmpty]
def fetchFilesFromGit(commit):
  files = []
  for filename in ['filling.root', 'topStorage.root', 'bottomStorage.root', 'topEmpty.root', 'bottomEmpty.root']:
    print('Fetching {0} from commit {1}'.format(filename, commit))
    buffer = subprocess.check_output(['git', 'show', commit + ':../results/' + filename])
    files.append( ROOT.TMemFile(filename, buffer, len(buffer)) )
  return files


def opposite(spin):
  if spin == 'hfs':
    return 'lfs'
  elif spin == 'lfs':
    return 'hfs'
  else:
    raise ValueError
    

# reads histograms from TFiles for each simulation stage
def readHistograms(fillingFile, topStorageFile, bottomStorageFile, topEmptyingFile, bottomEmptyingFile):
  histograms = {}

  for spin in ['hfs', 'lfs']:
    histograms['source'] = fillingFile.Get('spectrum')
    histograms['fill_top_' + spin] = fillingFile.Get('topCell_' + spin)
    histograms['fill_bottom_' + spin] = fillingFile.Get('bottomCell_' + spin)
    histograms['fill_spectrum_' + spin] = fillingFile.Get('spectrum_' + spin)

    histograms['storage_top_' + spin] = topStorageFile.Get('lifetime_' + spin)
    histograms['storage_bottom_' + spin] = bottomStorageFile.Get('lifetime_' + spin)
    histograms['storage_top_depolarized_' + spin] = topStorageFile.Get('lifetime_depolarized_' + spin)
    histograms['storage_bottom_depolarized_' + spin] = bottomStorageFile.Get('lifetime_depolarized_' + spin)
    histograms['storage_top_spectrum_' + spin] = topStorageFile.Get('spectrum_' + spin)
    histograms['storage_bottom_spectrum_' + spin] = bottomStorageFile.Get('spectrum_' + spin)

    histograms['hfsDetector_top_' + spin] = topEmptyingFile.Get('hfsDetector_' + spin)
    histograms['lfsDetector_top_' + spin] = topEmptyingFile.Get('lfsDetector_' + spin)
    histograms['hfsDetector_bottom_' + spin] = bottomEmptyingFile.Get('hfsDetector_' + spin)
    histograms['lfsDetector_bottom_' + spin] = bottomEmptyingFile.Get('lfsDetector_' + spin)
    histograms['emptying_top_spectrum_' + spin] = topEmptyingFile.Get('spectrum_' + spin)
    histograms['emptying_bottom_spectrum_' + spin] = bottomEmptyingFile.Get('spectrum_' + spin)

  h = topStorageFile.Get('centerofmass')
  if h: histograms['storage_top_centerOfMass'] = h
  h = bottomStorageFile.Get('centerofmass')
  if h: histograms['storage_bottom_centerOfMass'] = h
  
  for hist in histograms:
    histograms[hist].SetDirectory(0)
    histograms[hist].Sumw2()
  
  return histograms


# Calculate spectrum of neutron generated in source during valveClosedTime and fillTime
# histograms is the list of histograms read in with readHistograms
def startingSpectrum(histograms, valveClosedTime, fillTime, productionRate, uniqueName = '_py'):
  h = histograms['fill_spectrum_lfs']
  duration = h.GetXaxis().GetXmax() - h.GetXaxis().GetXmin()
  startBin = h.GetXaxis().FindBin(100. - valveClosedTime)
  endBin = h.GetXaxis().FindBin(100. + fillTime)
  h1 = histograms['fill_spectrum_lfs'].ProjectionY(uniqueName, startBin, endBin)
  h2 = histograms['fill_spectrum_hfs'].ProjectionY(uniqueName, startBin, endBin)
  spectrum = h1 + h2
  h1.Delete()
  h2.Delete()
  simulatedProductionRate = spectrum.GetEntries()/(valveClosedTime + fillTime)
  spectrum.Scale(productionRate/simulatedProductionRate)
  spectrum.SetDirectory(0)
  return spectrum


# Calculate spectrum of neutrons in one cell and one spin state after filling with valveClosedTime, fillTime, and productionRate
# histograms is the list of histograms read in with readHistograms
# cell is either 'top' or 'bottom'
# spin is either 'lfs' of 'hfs'
def fillingSpectrum(histograms, cell, spin, valveClosedTime, fillTime, productionRate, uniqueName = ''):
  histogram = histograms['fill_' + cell + '_' + spin]
  spectrum = histograms['fill_spectrum_' + spin]
  
  startBin = histogram.GetXaxis().FindBin(100. - valveClosedTime)
  fillBin = histogram.GetXaxis().FindBin(100. + fillTime)
  endBin = histogram.GetYaxis().FindBin(100. + fillTime)
  histogram.GetXaxis().SetRange(startBin, fillBin)
  histogram.GetYaxis().SetRange(endBin, endBin)
  h = histogram.Project3D('ze' + uniqueName) # get spectrum for spin state after valveClosedTime + fillTime
  h.Sumw2()
  simulatedProductionRate = spectrum.GetEntries()/(spectrum.GetXaxis().GetXmax() - spectrum.GetXaxis().GetXmin()) # calculate simulated production rate for spin state
  h.Scale(0.5*productionRate/simulatedProductionRate) # scale spectrum to real production rate for spin state (half of total production rate)
  h.SetDirectory(0)
  return h


# Calculate probability of UCN stored in one cell with given initial and final spin state surviving to storageTime
# histograms is the list of histograms read in with readHistograms
# cell is either 'top' or 'bottom'
# initial- and finalSpin are either 'lfs' or 'hfs'
def survivalProbabilitySpectrum(histograms, cell, initialSpin, finalSpin, storageTime, uniqueName = 'survProb'):
  if initialSpin != finalSpin:
    histogram = histograms['storage_' + cell + '_depolarized_' + initialSpin]
  else:
    histogram = histograms['storage_' + cell + '_' + initialSpin]
  spectrum = histograms['storage_' + cell + '_spectrum_' + initialSpin]
  
  bin = histogram.GetXaxis().FindBin(storageTime)
  h = histogram.ProjectionY(uniqueName, bin, bin)
  h.Sumw2()
  h.Divide(spectrum)
  h.SetDirectory(0)
  return h


# Calculate spectrum of UCN with one spin state after after filling and storing in one cell, including depolarization
# histograms is the list of histograms read in with readHistograms
# cell is either 'top' or 'bottom'
# spin is either 'lfs' or 'hfs'
def survivingSpectrum(histograms, cell, spin, valveClosedTime, fillTime, storageTime, productionRate, T2star):
#  h = fillingSpectrum(histograms, cell, spin, valveClosedTime, fillTime, productionRate) * survivalProbabilitySpectrum(histograms, cell, spin, spin, storageTime) \
#    + fillingSpectrum(histograms, cell, opposite(spin), valveClosedTime, fillTime, productionRate) * survivalProbabilitySpectrum(histograms, cell, opposite(spin), spin, storageTime)

# calculate polariation after storage based on survivalprobability spectra, add T2star depolarization on top
  h1f = fillingSpectrum(histograms, cell,          spin , valveClosedTime, fillTime, productionRate)
  h2f = fillingSpectrum(histograms, cell, opposite(spin), valveClosedTime, fillTime, productionRate)
  h3f = fillingSpectrum(histograms, cell, opposite(spin), valveClosedTime, fillTime, productionRate)
  h4f = fillingSpectrum(histograms, cell,          spin , valveClosedTime, fillTime, productionRate)
  h1s = survivalProbabilitySpectrum(histograms, cell,          spin ,          spin , storageTime)
  h2s = survivalProbabilitySpectrum(histograms, cell, opposite(spin),          spin , storageTime)
  h3s = survivalProbabilitySpectrum(histograms, cell, opposite(spin), opposite(spin), storageTime)
  h4s = survivalProbabilitySpectrum(histograms, cell, opposite(spin),          spin , storageTime)
  h1s.Scale(0.5*(1. + math.exp(-storageTime/T2star)))
  h2s.Scale(0.5*(1. + math.exp(-storageTime/T2star)))
  h3s.Scale(0.5*(1. - math.exp(-storageTime/T2star)))
  h4s.Scale(0.5*(1. - math.exp(-storageTime/T2star)))
  h = h1f*h1s + h2f*h2s + h3f*h3s + h4f*h4s
  h1f.Delete()
  h2f.Delete()
  h3f.Delete()
  h4f.Delete()
  h1s.Delete()
  h2s.Delete()
  h3s.Delete()
  h4s.Delete()

  h.SetDirectory(0)
  return h
  


# Calculate probability of UCN with one initial spin state stored in one nEDM cell to reach the detector for one final spin state within emptyingTime
# histograms is the list of histograms read in with readHistograms
# cell is either 'top' or 'bottom'
# detector is either 'lfs' (spin flipper on) or 'hfs' (spin flipper off)
# initialSpin is either 'lfs' or 'hfs'
def emptyingProbabilitySpectrum(histograms, cell, initialSpin, detector, emptyingTime, uniqueName = 'collProb'):
  histogram = histograms[detector + 'Detector_' + cell + '_' + initialSpin]
  spectrum = histograms['emptying_' + cell + '_spectrum_' + initialSpin]
  
  emptyBin = histogram.GetXaxis().FindBin(emptyingTime)
  h = histogram.ProjectionY(uniqueName, 0, emptyBin)
  h.Sumw2()
  h.Divide(spectrum)
  h.SetDirectory(0)
  return h


# Calculate spectrum of UCN that are detected in one detector after storage in cell
# histograms is the list of histograms read in with readHistograms
# cell is either 'top' or 'bottom'
# detector is either 'lfs' (spin flipper on) or 'hfs' (spin flipper off)
def emptyingSpectrumPolarized(histograms, cell, detector, spinPol,  valveClosedTime, fillTime, storageTime, emptyingTime, productionRate, T2star):
  hs = survivingSpectrum(histograms, cell, spinPol, valveClosedTime, fillTime, storageTime, productionRate, T2star) 
  he = emptyingProbabilitySpectrum(histograms, cell, spinPol , detector, emptyingTime) 
  h = hs * he
  h.SetDirectory(0)
  hs.Delete()
  he.Delete()
  return h

## Same as above, used for plotting
def emptyingSpectrum(histograms, cell, detector, valveClosedTime, fillTime, storageTime, emptyingTime, productionRate, T2star):
  h1 = emptyingSpectrumPolarized(histograms, cell, detector, 'lfs', valveClosedTime, fillTime, storageTime, emptyingTime, productionRate, T2star)
  h2 = emptyingSpectrumPolarized(histograms, cell, detector, 'hfs', valveClosedTime, fillTime, storageTime, emptyingTime, productionRate, T2star)
  h = h1 + h2
  h.SetDirectory(0)
  h1.Delete()
  h2.Delete()
  return h

# Calculate center of mass during storage period for detected UCN
# histograms is the list of histograms read in with readHistograms
# cell is either 'top' or 'bottom'
# detector is either 'lfs' (spin flipper on) or 'hfs' (spin flipper off)
def centerOfMass(histograms, cell, detector, valveClosedTime, fillTime, storageTime, emptyingTime, productionRate, T2star):
  spectrum = emptyingSpectrum(histograms, cell, detector, valveClosedTime, fillTime, storageTime, emptyingTime, productionRate, T2star)
  hname = 'storage_' + cell + '_centerOfMass'
  if hname in histograms: 
    weightedCOM = histograms[hname].ProfileX().ProjectionX() # mean of z for each energy bin <z>(H)
    weightedCOM.Multiply(spectrum) # <z>(H) N(H)
    weightedCOM.Scale(1./spectrum.Integral()) # <z>(H) N(H)/N
    COMerr = ctypes.c_double(0.)
    centerOfMass = weightedCOM.IntegralAndError(0, -1, COMerr) # COM = integral <z>(H) N(H)/N dH
    weightedCOM.Delete()

    weightedVar = histograms[hname].ProfileX().ProjectionX() # mean of z for each energy bin <z>(H)
    for bin in range(weightedVar.GetNbinsX()):
      weightedVar.SetBinContent(bin, weightedVar.GetBinContent(bin) - centerOfMass) # <z>(H) - <z>
    weightedVar.Multiply(weightedVar) # (<z>(H) - <z>)^2
    weightedVar.Multiply(spectrum) # (<z>(H) - <z>)^2 N(H)
    weightedVar.Scale(1./spectrum.Integral()) # (<z>(H) - <z>)^2 N(H)/N
    COMvarErr = ctypes.c_double(0.)
    COMvar = weightedVar.IntegralAndError(0, -1, COMvarErr) # Var COM = integral (<z>(H) - <z>)^2 N(H)/N dH
    weightedVar.Delete()

    return centerOfMass, COMerr.value, COMvar, COMvarErr.value
  return 0., 0., 0., 0.
