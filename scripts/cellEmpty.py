import sys
import ROOT
import os.path

ROOT.gROOT.SetBatch(1)

if len(sys.argv) == 1:
  print('No filenames given in command-line parameters!')
  exit()
  
detectors = ROOT.TCut('solidend == 320 || solidend == 321')
hfs_detectors = '(solidend == 139 || solidend == 163)' # detectors without spin flipper
lfs_detectors = '(solidend == 138 || solidend == 162)' # detectors with spin flipper

neutronend = ROOT.TChain("neutronend")
#neutronsnapshot = ROOT.TChain("neutronsnapshot")

for file in sys.argv[1:]:
  neutronend.Add(file)
#  neutronsnapshot.Add(file)
  
filename = os.path.dirname(sys.argv[1]) + '/out_DetEff.root'
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

c = ROOT.TCanvas('d', 'd')
neutronend.Draw('Hstart*1e9 >> spectrum(50, 0, 250)')
spectrum = ROOT.gDirectory.Get('spectrum')

neutronend.Draw('Hstart*1e9:tend >> emptyEff(250, 0, 250, 50, 0, 250)', detectors)
emptyEff = ROOT.gDirectory.Get('emptyEff')

neutronend.Draw('Hstart*1e9 >> spectrum_lfs(50, 0, 250)', 'polstart == 1')
neutronend.Draw('Hstart*1e9 >> spectrum_hfs(50, 0, 250)', 'polstart == -1')
neutronend.Draw('Hstart*1e9:tend >> hfsDetector_hfs(250, 0, 250, 50, 0, 250)', hfs_detectors + ' && polstart == -1')
neutronend.Draw('Hstart*1e9:tend >> lfsDetector_lfs(250, 0, 250, 50, 0, 250)', lfs_detectors + ' && polstart == 1')
neutronend.Draw('Hstart*1e9:tend >> hfsDetector_lfs(250, 0, 250, 50, 0, 250)', hfs_detectors + ' && polstart == 1')
neutronend.Draw('Hstart*1e9:tend >> lfsDetector_hfs(250, 0, 250, 50, 0, 250)', lfs_detectors + ' && polstart == -1')

def ScaleHist2D(hist2D, hist1D):
  for Hbin in range(hist2D.GetNbinsY() + 1):
    scale = hist1D.GetBinContent(Hbin)
    for tbin in range(hist2D.GetNbinsX() + 1):
      bin = hist2D.GetBin(tbin, Hbin)
      if scale > 0:
        hist2D.SetBinContent(bin, hist2D.GetBinContent(bin)/scale)
        hist2D.SetBinError(bin, hist2D.GetBinError(bin)/scale)
      else:
        hist2D.SetBinContent(bin, 0)
        hist2D.SetBinError(bin, 0)
  hist2D.Sumw2()
  
ScaleHist2D(emptyEff, spectrum)
emptyEff.Draw('LEGO')


ROOT.gStyle.SetOptStat(0)
ROOT.gROOT.ForceStyle()
neutronend.Draw('Hstart*1e9 >> detEff(50, 0, 250)', detectors)
detEff = ROOT.gDirectory.Get('detEff')
detEff.Sumw2()
detEff.Divide(spectrum);
detEff.SetTitle('Collection efficiency of detector vs Energy for {0}'.format(filename));
detEff.GetXaxis().SetTitle("Energy (neV)");
detEff.GetYaxis().SetTitle("Collection efficiency");
detEff.GetXaxis().SetTitleSize(0.05);
detEff.GetXaxis().SetTitleOffset(0.90);
detEff.GetYaxis().SetTitleSize(0.05);
detEff.GetYaxis().SetTitleOffset(0.75);
detEff.GetXaxis().SetLabelSize(0.05);
detEff.GetYaxis().SetLabelSize(0.05);
detEff.Draw();


neutronend.Draw('tend >> countRate(200, 0, 200)', detectors)
countRate = ROOT.gDirectory.Get('countRate')
countRate.SetTitle('DetectorCountRate {0}'.format(filename));
countRate.GetXaxis().SetTitle("Time (s)");
countRate.GetYaxis().SetTitle("Counts");
normalize = 1.45E6 / countRate.GetEntries();
countRate.Scale(normalize);
countRate.Draw("HIST");


outfile.Write()
outfile.Close()
