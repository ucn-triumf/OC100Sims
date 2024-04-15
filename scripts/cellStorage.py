import sys
import ROOT
import os.path

ROOT.gROOT.SetBatch(1)

if len(sys.argv) == 1:
  print('No filenames given in command-line parameters!')
  exit()
  
neutronend = ROOT.TChain("neutronend")
neutronsnapshot = ROOT.TChain("neutronsnapshot")

EDMcell = '(solidend == 303 )'

for file in sys.argv[1:]:
  neutronend.Add(file)
  neutronsnapshot.Add(file)
  
filename = os.path.dirname(sys.argv[1]) + '/out_hist.root'
outfile = ROOT.TFile(filename, 'RECREATE')

configFile = ROOT.TFile(sys.argv[1], 'READ') # read config from first ROOT file
configSrc = configFile.Get('config')
if configSrc:
  configDst = outfile.mkdir('config')
  for sectionName in configSrc.GetListOfKeys():
    sectionDst = configDst.mkdir(sectionName.GetName())
    sectionSrc = configSrc.Get(sectionName.GetName())
    for varName in sectionSrc.GetListOfKeys():
      sectionDst.WriteTObject(sectionSrc.Get(varName.GetName()), varName.GetName())
outfile.cd()

arr = ROOT.TObjArray()
tauFit = ROOT.TF1('tauFit', '[0]*exp(-x/[1])')
tauFit.SetParameters(100, 50)

c = ROOT.TCanvas('d', 'd', 800, 600)
neutronsnapshot.Draw('Hend*1e9:tend >> lifetime(200, 0, 200, 50, 0, 250)', EDMcell, 'LEGO')
lifetime = ROOT.gDirectory.Get('lifetime')
lifetime.FitSlicesX(tauFit, 0, -1, 0, 'Q', arr)
tauVSh = arr[1]
c.SetLogy(1)
tauVSh.SetTitle('Storage lifetime vs Energy for {0}'.format(filename));
tauVSh.GetXaxis().SetTitle("Energy (eV)");
tauVSh.GetYaxis().SetTitle("Storage lifetime (s)");
tauVSh.Draw();

neutronsnapshot.Draw('Hend*1e9:tend >> lifetime_lfs(300, 0, 300, 50, 0, 250)', EDMcell + '&& polstart == 1 && polend == 1', 'LEGO')
neutronsnapshot.Draw('Hend*1e9:tend >> lifetime_hfs(300, 0, 300, 50, 0, 250)', EDMcell + '&& polstart == -1 && polend == -1', 'LEGO')
neutronsnapshot.Draw('Hend*1e9:tend >> lifetime_depolarized_lfs(300, 0, 300, 50, 0, 250)', EDMcell + '&& polstart == 1 && polend == -1', 'LEGO')
neutronsnapshot.Draw('Hend*1e9:tend >> lifetime_depolarized_hfs(300, 0, 300, 50, 0, 250)', EDMcell + '&& polstart == -1 && polend == 1', 'LEGO')

neutronend.Draw('Hstart*1e9 >> spectrum_lfs(50, 0, 250)', 'polstart == 1')
neutronend.Draw('Hstart*1e9 >> spectrum_hfs(50, 0, 250)', 'polstart == -1')


neutronsnapshot.Draw('zend:Hend*1e9 >> centerofmass(50, 0, 250, 50, -0.25, 0.25)')


outfile.Write()
outfile.Close()
