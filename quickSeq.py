import os
import re

RE_STEREO = re.compile('(%V)')
RE_LEFT = re.compile('(left|Left)')
RE_RIGHT = re.compile('(right|Right)')
RE_LEFT_RIGHT = re.compile('(left|Left|right|Right)')

RE_FORMAT = re.compile("(\%0(\d)d)")
RE_NUMBERED = re.compile('(\d+)(?=\.)')
RE_PADDING = re.compile('(#+)(?=\.)')

URL_VIEW_TYPES = [
	'mono',
	'left',
	'right',
	'stereo',
]

class Seq:
	def __init__(self, url, first=None, last=None):
		self.url = os.path.abspath(url)
		if not self._isSequence():
			raise ValueError('Url is has no padding: {0}'.format(self.url))
		self.head = ''
		self.nLength = 0
		self.tail = ''
		self._setParts()
		self.first = first
		self.last = last
		self.viewType = self.getViewType()

	def __repr__(self):
		return "<Seq object> {0}%0{1}d{2}".format(self.head, self.nLength, self.tail)

	def _isSequence(self):
		format_obj = RE_FORMAT.search(self.url)
		padding_obj = RE_PADDING.search(self.url)
		if not (format_obj or padding_obj):
			return False
		return True

	def _setParts(self):
		format_obj = RE_FORMAT.search(self.url)
		padding_obj = RE_PADDING.search(self.url)
		if padding_obj:
			self.head = self.url[:padding_obj.start(1)]
			self.tail = self.url[padding_obj.end(1):]
			self.nLength = len(padding_obj.group(1))
		elif format_obj:
			self.head = self.url[:format_obj.start(1)]
			self.tail = self.url[format_obj.end(1):]
			self.nLength = int(format_obj.group(2))

	def hasRange(self):
		if self.first and self.last:
			return True
		return False

	def listFramesFromRange(self):
		frames = []
		if self.hasRange():
			for f in range(self.first, self.last+1):
				nFile = self.head + str(f).zfill(self.nLength) + self.tail
				frames.append(nFile)
		return frames

	def framesExists(self):
		if not self.hasRange():
			return False
		for f in self.listFrames():
			if not os.path.exists(f):
				return False
		return True

	def setRangeFromBiggestChunk(self): # does not consider previous range
		paths = self.findBiggestChunk()
		if paths:
			patt = "(\d{0})".format("{"+str(self.nLength)+"}")
			reObj = re.search(patt,paths[0] )
			self.first = int(reObj.group(1))
			reObj = re.search(patt,paths[-1] )
			self.last = int(reObj.group(1))

	def findExistingFrames(self): # does not consider previous range
		dir = os.path.split(self.head)[0]
		files = os.listdir(dir)

		#list matches to sequence pattern
		worthy = []
		for f in files:
			patt = "(\d{0})(?=\.)".format("{"+str(self.nLength)+"}")
			fullpath = os.path.join(dir, f)
			reObj = re.search(patt,fullpath )
			if reObj:
				if fullpath[:reObj.start(1)] == self.head:
					if fullpath[reObj.end(1):] == self.tail:
						worthy.append(fullpath)

		return worthy

	def findBiggestChunk(self):
		worthy = self.findExistingFrames()
		#chunk sublists ie: [1-10], [12-15], [18-22]
		if worthy:
			worthy.sort()
			subSequences = []
			sub = []
			last = None
			patt = "(\d{0})(?=\.)".format("{"+str(self.nLength)+"}")
			for i in worthy:
				reObj = re.search(patt, i)
				n = int(reObj.group(0))

				if last == None:
					sub.append(i)
					last = n
				else:
					if n == last+1:
						sub.append(i)
						last = n
					else:
						subSequences.append(sub)
						sub = []
						last = None
			subSequences.append(sub)

			#find the longest sublist
			if subSequences:
				return max(subSequences, key=len)

		return []

	def getViewType(self):
		isStereo = RE_STEREO.search(self.url)
		isLeft = RE_LEFT.search(self.url)
		isRight = RE_RIGHT.search(self.url)

		if isStereo:
			return URL_VIEW_TYPES[3]
		elif isLeft:
			return URL_VIEW_TYPES[1]
		elif isRight:
			return URL_VIEW_TYPES[2]
		else:
			return URL_VIEW_TYPES[0]