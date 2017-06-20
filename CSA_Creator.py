import sys, os, lzss, subprocess
from gbaspritesheet import *
from OAM import *
from gbaimage import *
from tilemap import *

def b_to_hex(data, width=1):
  '''Takes a bytes object and returns BYTE AA BB CC DD'''
  w = "BYTE"
  if width==2:
    w= "SHORT"
  elif width==4:
    w= "WORD"
  return '{} '.format(w) + ' '.join([hex(x) for x in data])

class SpellCreator(object):
  """docstring for SpellCreator"""
  def __init__(self, script_path):
    super(SpellCreator, self).__init__()
    self.name = os.path.split(script_path)[1]
    self.name = os.path.splitext(self.name)[0].replace(' ','_').replace('-','_')
    if self.name[0].isdigit():
      self.name = '_'+self.name
    self.usedObjGraphics = {} # a dict of graphics path=>index
    self.usedBgGraphics = {} # same for bg
    self.objGraphics = [] # list of GBAImage objects
    self.objSheets = [] # list of GBASpriteSheet objects
    self.objPals = [] # index of palettes(bytes format)


    self.framedata = self.name + "_framedata:\n"
    self.tsaOutput = "//TSA Data\n"
    self.bgGraphicsOutput = "//BG Graphics Data\n"
    self.bgPalettesOutput = "//BG Palettes Data\n"
    self.objGraphicsOutput = "//OBJ Sheets Data\n"
    self.objPalettesOutput = "//OBJ Palettes Data\n" # is there only one? There ARE multiple frames per sheet...
    self.oamOutput = "//OAM Data\n"
    # todo: check for same frames
    # self.frameCommands = []
    self.framecount = 0
    self.commandcount = 0
    self.rtlOAMList = []
    self.ltrOAMList = []
    self.bgrtlOAMList = []
    self.bgltrOAMList = []
    self.queuedObjImg = None
    self.queuedBGImg = None
    self.path = script_path
    self.scriptpath = os.path.dirname(os.path.realpath(sys.argv[0]))

  def processScript(self):
    """Processes a script file, then returns the output as a string"""
    with open(self.path,'r') as script:
      lines = script.readlines()
      script = [line.strip() for line in lines if (line.strip() != "")]
    for line in script:
      if line[0] == "C":
        self.addCommand(line)
      elif line[0] == "O":
        self.queueOBJ(line)
      elif line[0] == "B":
        self.queueBG(line)
      elif line[0] == "~":
        self.addMissTerminator()
      elif line[0].isdigit():
        duration = int(line)
        self.addFrame(duration)
    self.framedata += "WORD 0x80000000\n"
    self.updateSheets()
    self.updateObjPal()
    self.updateOAMs()
    output = self.updateOutput()
    outfile = os.path.splitext(self.path)[0]+'.event'
    with open(outfile,'w') as f:
      f.write(output)

  def updateOutput(self):
    return """//Spell Animation generated by CSA inserter

#define {spell}_index SPELL_INDEX //Change SPELL_INDEX to whatever spell you're replacing
setCustomSpell_dim({spell}_index) //change to "setCustomSpell_nodim" to skip screen dimming

setCSATable({spell}_index, {spell}_framedata, {spell}_rtl_fg, {spell}_ltr_fg, {spell}_rtl_bg, {spell}_ltr_bg)


ALIGN 4
{framedata}
{oam}
{tsa}
{objsheets}
{objpal}
{bgsheets}
{bgpal}
""".format(spell=self.name,framedata=self.framedata,oam=self.oamOutput,tsa=self.tsaOutput,objsheets=self.objGraphicsOutput,objpal=self.objPalettesOutput,bgsheets=self.bgGraphicsOutput,bgpal=self.bgPalettesOutput)
    
  def addMissTerminator(self):
    self.framedata += "WORD 0x80000100\n"

  def updateOAMs(self):
    """make the flipped oams, then serialize"""
    for oam in self.rtlOAMList:
      if oam:
        self.ltrOAMList.append(oam.flipped())
      else:
        self.ltrOAMList.append(None)
    for oam in self.bgrtlOAMList:
      if oam:
        self.bgltrOAMList.append(oam.flipped())
      else:
        self.bgltrOAMList.append(None)
    # now serialize them and add to output
    self.oamOutput += "{}_rtl_fg:\n".format(self.name)+(b_to_hex(self.serializeOAMs(self.rtlOAMList))+'\n')
    self.oamOutput += "{}_ltr_fg:\n".format(self.name)+(b_to_hex(self.serializeOAMs(self.ltrOAMList))+'\n')
    self.oamOutput += "{}_rtl_bg:\n".format(self.name)+(b_to_hex(self.serializeOAMs(self.bgrtlOAMList))+'\n')
    self.oamOutput += "{}_ltr_bg:\n".format(self.name)+(b_to_hex(self.serializeOAMs(self.bgltrOAMList))+'\n')

  def updateObjPal(self):
    self.objPalettesOutput += "{}_objPalette:\n".format(self.name)+b_to_hex(self.objSheets[0].image.palette,2)+'\n'

  def updateSheets(self):
    for index, sheet in enumerate(self.objSheets):
      self.objGraphicsOutput += "{}_objimg_{}:\n".format(self.name,index)
      data = b_to_hex(lzss.compress(sheet.image.image))
      self.objGraphicsOutput+= data+'\n'

  def addCommand(self, line):
    command = int("0x"+line[1:],16)
    self.framedata += ("WORD "+ hex(command|0x85000000) + "\n")

  def queueOBJ(self, line):
    path = line[1:].strip()
    self.queuedObjImg = GBAImage(path)

  def queueBG(self, line):
    path = line[1:].strip()
    self.queuedBGImg = path

  def processBG(self,path):
    """takes a 256x160 indexed 16 colour image with 256 unique tiles.
    Adds a new one, or finds a matching old one. Returns the index."""
    basepath = os.path.split(path)[1]
    basepath = os.path.splitext(basepath)[0]
    try:
      index = self.usedBgGraphics[basepath]
    except KeyError:
      self.gritify(path)
      index = len(self.usedBgGraphics)
      self.usedBgGraphics[basepath] = index
      #todo: add graphics installers
      self.tsaOutput += '{}_TSA_{}:\n#incbin "{}.map.bin"\n'.format(self.name,index,basepath)
      self.bgGraphicsOutput += '{}_bgImage_{}:\n#incbin "{}.img.bin"\n'.format(self.name,index,basepath)
      self.bgPalettesOutput += '{}_bgPalette_{}:\n#incbin "{}.pal.bin"\n'.format(self.name,index,basepath)
    return index

  def gritify(self,path):
    grit_path = os.path.join(os.path.join(self.scriptpath, "grit"), 'grit')
    # i need a way to tell what the top right pixel is
    transparentcolour = getTopRight(path)
    # command = '"{}" "{}" -gB 4 -gzl -m -mLf -mR4 -mzl -pn 16 -ftb -fh!'.format(grit_path, path)
    # print('HEY\n', command)
    # os.system(command)
    if transparentcolour==None: #if 0 was in the top right, assume it's the transparent colour
      subprocess.run([grit_path, path, '-gB', '4', '-gzl', '-m', '-mLf', '-mR4', '-mzl', '-pn', '16', '-ftb', '-fh!', '-ah', '160', '-aw', '240'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else: #otherwise, assume black is the transparent colour.
      subprocess.run([grit_path, path, '-gB', '4', '-gzl', '-m', '-mLf', '-mR4', '-mzl', '-pn', '16', '-ftb', '-fh!', '-ah', '160', '-aw', '240', '-gT', transparentcolour], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  def processFrame(self,image):
    w = image.width
    h = image.height
    result = [GBAImage.imageFromSlice(image,0,0,30,20),GBAImage.imageFromSlice(image,30,0,30,20)]
    return result

  def serializeOAMs(self, oams):
    result = bytearray((len(oams)*12))
    index = 0
    for i in range(len(oams)):
      index = OAM.serialize(oams[i], result, index)
    return result

  def setUpGraphics(self,palette):
    if len(self.objSheets)>0:
      return
    first = GBASpriteSheet(palette,32,4)
    self.objSheets.append(first)

  def addFrame(self,duration):
    objImage = self.queuedObjImg
    bgImage = self.queuedBGImg
    duration &= 0xFFFF # let's just fail gracefully
    images = self.processFrame(objImage)
    bgSheetIndex = self.processBG(bgImage) # this is different because grit
    self.setUpGraphics(images[0].palette)
    # todo: check if images are the same (don't use the feditor way, just check the path lol)
    objPalIndex = len(self.objPals)
    self.objPals.append(objImage.palette)
    # todo: check if any of these are repeats
    # do i actually need to add anything to these guys???
    fgTileMap = TileMap(images[0])
    bgTileMap = TileMap(images[1])
    usedTiles = fgTileMap.getCount() + bgTileMap.getCount()
    print(usedTiles)
    assert usedTiles <= 0x80, "Error - too many tiles"
    #prepare OAM data
    fgOAMData = OAM.calculateOptimumOAM(fgTileMap)
    bgOAMData = OAM.calculateOptimumOAM(bgTileMap)
    allOAMData = fgOAMData+bgOAMData
    sheetIndex = OAM.selectSheet(OAM,images[0],images[1],allOAMData,self.objSheets, True) #passes in the two images, the oam data, the existing sheets.
    fgOAMdest = len(self.rtlOAMList)
    # todo: check if OAM identical
    self.rtlOAMList += fgOAMData
    bgOAMdest = len(self.bgrtlOAMList)
    # same, check
    self.bgrtlOAMList += bgOAMData
    #the TSA index might change...? We'll want to return an index from processBG i think.
    self.framedata+="SHORT {duration}; BYTE {framecount} 0x86; POIN {name}_objimg_{objid}; WORD {fgoamid} {bgoamid}; POIN {name}_bgImage_{bgid} {name}_objPalette {name}_bgPalette_{bgid} {name}_TSA_{bgid}\n".format(name=self.name,duration=duration, framecount=self.framecount, fgoamid=fgOAMdest*12, bgoamid=bgOAMdest*12, bgid=bgSheetIndex, objid=sheetIndex)
    self.framecount += 1
    print("processed frame {}".format(self.framecount))

def show_exception_and_exit(exc_type, exc_value, tb):
  import traceback
  traceback.print_exception(exc_type, exc_value, tb)
  input("Press Enter key to exit.")
  sys.exit(-1)

def main():
  sys.excepthook = show_exception_and_exit
  assert len(sys.argv) > 1, "No script given."
  a = SpellCreator(sys.argv[1])
  a.processScript()

if __name__ == '__main__':
  main()