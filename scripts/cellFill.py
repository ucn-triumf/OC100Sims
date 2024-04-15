import sys
import ROOT
import os.path

ROOT.gROOT.SetBatch(1)

if len(sys.argv) == 1:
  print('No filenames given in command-line parameters!')
  exit()
  
bottomCell = 'solidend == 303'
  
neutronend = ROOT.TChain("neutronend")
neutronsnapshot = ROOT.TChain("neutronsnapshot")

for file in sys.argv[1:]:
  neutronend.Add(file)
  neutronsnapshot.Add(file)
  
filename = os.path.dirname(sys.argv[1]) + '/out_fill.root'
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

c = ROOT.TCanvas('d', 'd', 800, 600)
neutronsnapshot.Draw('Hend*1e9:tend:tstart >> bottomCell(250, 0, 250, 250, 0, 250, 50, 0, 250)', bottomCell)
fill_bottom = ROOT.gDirectory.Get('bottomCell')

neutronsnapshot.Draw('Hend*1e9:tend:tstart >> bottomCell_lfs(250, 0, 250, 250, 0, 250, 50, 0, 250)', bottomCell + ' && polend == 1')
fill_bottom_lfs = ROOT.gDirectory.Get('bottomCell_lfs')

neutronsnapshot.Draw('Hend*1e9:tend:tstart >> bottomCell_hfs(250, 0, 250, 250, 0, 250, 50, 0, 250)', bottomCell + ' && polend == -1')
fill_bottom_hfs = ROOT.gDirectory.Get('bottomCell_hfs')

neutronend.Draw('Hstart*1e9 >> spectrum(60, -50, 250)')
spectrum = ROOT.gDirectory.Get('spectrum')

neutronend.Draw('Hstart*1e9:tstart >> spectrum_lfs(250, 0, 250, 60, -50, 250', 'polstart == 1')
spectrum_lfs = ROOT.gDirectory.Get('spectrum_lfs')
neutronend.Draw('Hstart*1e9:tstart >> spectrum_hfs(250, 0, 250, 60, -50, 250', 'polstart == -1')
spectrum_hfs = ROOT.gDirectory.Get('spectrum_hfs')

neutronend.Draw('tend-tstart>>lifetime(90,10,100)','tstart<5')
lifetime = ROOT.gDirectory.Get('lifetime')

neutronend.Draw("tend-tstart>>sysLifetime(130, 10, 140)","tstart>100 && tstart<105")
sysLifetime = ROOT.gDirectory.Get("sysLifetime")

fill_bottom.Project3D('y')

outfile.Write()
outfile.Close()
