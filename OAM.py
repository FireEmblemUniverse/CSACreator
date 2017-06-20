import tilemap, gbaimage, gbaspritesheet, copy

""" with this, we can calculate the optimum oam and stuff.
"""

class OAM(object):

    def __init__(self, input):
        # FIXME: Stop using 'null' for terminators. Do subclassing instead, like
        # the AnimationCommand hierarchy. It's cleaner.
        self._square = 0
        self._horizontal = (1 << 6)
        self._vertical = (2 << 6)
        self._times1 = 0
        self._times2 = (1 << 6)
        self._times4 = (2 << 6)
        self._times8 = (3 << 6)
        self._tile_scale = 8
        self.image_x = input[0]
        self.image_y = input[1]
        self.width = input[2]
        self.height = input[3]
        self.is_flipped = False
        self.sheet_y = self.sheet_x = 0
        self.vram_x = self.vram_y = 0

    def serialize(oam, buffer, index):
        if oam == None:
            buffer[index] = 1 #this is like a terminator for the frame.
            return index + 12
        return oam.do_serialization(buffer, index)

    serialize = staticmethod(serialize)

    def cerealize(oam):
        lol = bytearray(12)
        oam.do_serialization(lol, 0)
        out = "BYTE"
        for l in lol:
            out += " "
            out += hex(l)
        print(out)

    def do_serialization(self, buffer, index):
        height, width = self.height, self.width

        if width > height:
            buffer[index + 1] = self._horizontal
        elif height > width:
            buffer[index + 1] = self._vertical
        else:
            buffer[index + 1] = self._square

        #if (width * height == 64) or (width * height == 32):
            #buffer[index + 3] = self._times8
        if (width * height == 16) or (width * height == 8):
            buffer[index + 3] = self._times4
        elif (width * height == 4):
            buffer[index + 3] = self._times2
        elif (width * height == 2) or (width * height == 1):
            buffer[index + 3] = self._times1
        else:
            raise Exception
        if self.is_flipped:
            buffer[index + 3] |= 0x10
        buffer[index + 4] = ((self.sheet_y << 5) | self.sheet_x)
        buffer[index + 6] = (self.vram_x+(1<<32))&0xFF
        buffer[index + 7] = (((self.vram_x+(1<<32))&0xFFFF) >> 8)
        buffer[index + 8] = (self.vram_y+(1<<32))&0xFF
        buffer[index + 9] = (((self.vram_y+(1<<32))&0xFFFF) >> 8)
        return index+12

    def calculateOptimumOAM(tilemap):
        optimumOAMData = []
        searchsizes = [
            #(8,8),
            #(4,8),
            #(8,4),
            (4,4),
            (2,4),
            (4,2),
            (2,2),
            (1,4),
            (4,1),
            (2,1),
            (1,2),
            (1,1)
        ]
        for searchsize in searchsizes:
            while True:
                region = tilemap.extractMarkedRegion(searchsize[0],searchsize[1])
                if region == None:
                    break
                optimumOAMData.append(OAM(region))

        optimumOAMData.append(None)
        return optimumOAMData

    def setVRAMLocation(self,spell=True):
        self.vram_x = (self.image_x * self._tile_scale) - (0xAC if spell else 0x94)
        self.vram_y = (self.image_y * self._tile_scale) - 0x58

    def setSheetLocation(self, x, y):
        self.sheet_x, self.sheet_y = x,y

    def flipped(self):
        """returns a flipped copy of itself."""
        result = OAM([self.image_x,self.image_y,self.width,self.height])
        result.vram_x = -(self.width*8) - self.vram_x
        result.vram_y = self.vram_y
        result.sheet_x = self.sheet_x
        result.sheet_y = self.sheet_y
        result.is_flipped = True
        return result

    def regionOfSourceimage(self,image):
        return gbaimage.GBAImage.imageFromSlice(image,self.image_x,self.image_y,self.width,self.height)

    def canFitOAM(self, fg, bg, oamsize, originalsheet, spell=True):
        sheet = copy.copy(originalsheet)
        bg_mode = False
        for oam in oamsize:
            if oam == None:
                bg_mode=True
                continue
            sprite = oam.regionOfSourceimage(bg if bg_mode else fg)
            location = sheet.findInsertionLocation(sprite)
            if not location:
                return False
            x,y = location
            oam.setSheetLocation(x,y)
            oam.setVRAMLocation(spell)
            if not sheet.usedTileAt(x,y):
                sheet.blit(sprite,x,y) #this writes it to the sheet's image
        originalsheet = sheet
        return True

    def selectSheet(self, fg, bg, oamsizes, oamsheets, spell=True):
        """ it says select, but it also writes the data to the sheet"""
        assert(len(oamsheets)>0), "oamsheets is empty"
        index = 0
        while index < len(oamsheets):
            if self.canFitOAM(self, fg, bg, oamsizes, oamsheets[index], spell): #finds the first sheet we can fit it on
                break
            index += 1
        if index==len(oamsheets): #none was found
            to_add = gbaspritesheet.GBASpriteSheet(fg.palette,32,4) #clean spritesheet
            assert self.canFitOAM(self, fg, bg, oamsizes, to_add, spell), "Error: cannot fit on blank sheet"
            oamsheets.append(to_add)
        return index

if __name__ == '__main__':
    # tp = gbaimage.GBAImage("test.png")
    # tm = tilemap.TileMap(tp)
    # buffeer = bytearray(12)
    # opt = OAM.calculateOptimumOAM(tm)
    # flip = [x.flipped() for x in opt if x]
    a = [1,2,3]
    a += ([4,5,6])
    a.append(None)
    print(a)