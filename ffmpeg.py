import os
import re
import subprocess
import pprint
import math
import quickSeq

rePad = re.compile("(\%0(\d)d)")
reRatio = re.compile("(\:)")
reRate = re.compile("(\/)")


##########
# INPUTS #
##########
class Input:
	TYPES = [
		'sequence',
		'video'
	]
	VIDEO_EXT = [
		'.mov',
		'.mp4',
	]
	args = [
		[													# Sequence args
			["-probesize", "5000000"],	# probe on a larger size than usual to get more data
			["-f", "image2"],						# specify image demuxer
			["-framerate", ""],				# interprete fps
			["-i", ""],									# input url
		],
		[															# video args
			["-i", ""],									# input url
		]
	]

	def __init__(self, url):
		self.url = url
		summary = Input.probeSource(self.url)
		self.vStreamsCount = summary['streams']['video_streams_count']
		self.aStreamsCount = summary['streams']['audio_streams_count']
		self.vFirstStreamProperties = summary['videoStreamProperties']
		ext =  os.path.splitext(url)[1]
		self.type = Input.TYPES[1] if ext in Input.VIDEO_EXT else Input.TYPES[0]
		self.codec = self.vFirstStreamProperties['codec_name']
		self.w = self.vFirstStreamProperties['width']
		self.h = self.vFirstStreamProperties['height']
		self.sar = self.vFirstStreamProperties['sample_aspect_ratio'].replace(":", "/")
		self.dar = self.vFirstStreamProperties['display_aspect_ratio'].replace(":", "/")
		self.fps = self.vFirstStreamProperties['r_frame_rate']
		self.duration = self.vFirstStreamProperties['duration']

	def setType(self, idx):
			self.type = Input.TYPES[idx]

	def setFramerate(self, fps):
			self.fps = str(fps) if str(fps).count('/')>0 else str(fps)+'/1'

	def getFramerateString(self):
		val = float("{0:.2f}".format(eval(self.fps)))
		return val if not val.is_integer() else int(val)

	def getFramesCount(self):
		return int(round(float(self.duration)*float(eval(self.fps))))

	def getDuration(self):
		d = float(self.duration)
		f = int(math.floor(float(d%1)*float(eval(self.fps))))
		s = int(math.floor(d%60))
		m = int(math.floor((d/60)%60))
		h = int(math.floor((d/3600)%60))
		return "{0};{1};{2};{3}".format(str(h).zfill(2), str(m).zfill(2), str(s).zfill(2), str(f).zfill(2))

	def getShortUrl(self):
		drive, p = os.path.splitdrive(self.url)
		head, tail = os.path.split(p)
		return  '{0}...{1}{2}'.format( drive, os.sep, tail)

	def generateArgsList(self):
		args = []
		for i in Input.args[Input.TYPES.index(self.type)]:
			if isinstance(i, list):
				args.append(i[0])
				if i[0] == '-framerate':
					args.append(self.fps)
				elif i[0] == '-i':
					args.append(self.url)
				else:
					args.append(i[1])
			elif isinstance(i, str):
				args.append(i)
		return args

	def generateArgsString(self):
		return " ".join(self.generateArgsList())

	def summary(self):
		return '{0}\n{1}x{2} ({3}), {4} fps\n{5}, {6} frames\nvStreams:{7} aStreams:{8}'.format(
						self.getShortUrl(), self.w, self.h, self.sar, self.getFramerateString(),
						self.getDuration(), self.getFramesCount(), self.vStreamsCount, self.aStreamsCount)

	@classmethod
	def probeSource(cls, source):
		# ref: https://trac.ffmpeg.org/wiki/FFprobeTips
		sourceData = {
			"streams": {
				"video_streams_count": None, #2
				"audio_streams_count": None, #2
			},
			"videoStreamProperties": {
				"codec_name": None, #h264
				"width":None, #1920
				"height":None, #1080
				"sample_aspect_ratio":None, # 1/1
				"display_aspect_ratio":None, # 16:9
				"bit_rate":None, # 12700   *video only*
				"r_frame_rate":None, # 24000/1001
				"duration":None, # 366.82500  (seconds)
			}
		}
		# Streams basic info
		sourceData["streams"]["video_streams_count"] = bytes.decode(subprocess.check_output(
																									['ffprobe', '-v', 'quiet', '-select_streams', 'v',
							 																		'-show_entries', 'stream=codec_type','-of', 'default=nw=1:nk=1',
							 																		'{0}'.format(source)]
																								)).replace("\r\n", "").count('video')

		sourceData["streams"]["audio_streams_count"] = bytes.decode(subprocess.check_output(
																									['ffprobe', '-v', 'quiet', '-select_streams', 'a',
																									'-show_entries', 'stream=codec_type','-of', 'default=nw=1:nk=1',
																									'{0}'.format(source)]
																								)).replace("\r\n", "").count('audio')

		#video stream properties
		for key, val in sourceData["videoStreamProperties"].items():
			probeValue = bytes.decode(subprocess.check_output(['ffprobe',  '-v', 'quiet', '-select_streams', 'v:0',
				'-show_entries', 'stream={0}'.format(key), '-of', 'default=nw=1:nk=1', '{0}'.format(source)])).replace("\r\n", "")
			# todo: filter and convert "N/A" and others similar to None
			if probeValue == "N/A":
				probeValue = None
			sourceData["videoStreamProperties"][key] = probeValue
		return sourceData


###########
# FILTERS #
###########
class Filter:
	def __init__(self, name):
		self.name = name

	def generateArgsString(self):
		return str(self.name)

class Scale(Filter):
	# Scaling filter. 0=same as input, -1=keep ratio
	# "scale=1280:720"
	MODES = [
		'values',
		'matchSource',
		'halfSource',
		'halfWidthSource',
		'halfHeightSource',
		'TwiceWidthSource',
		'TwiceHeightSource',
	]
	def __init__(self, w=0, h=0):
		Filter.__init__(self, "scale")
		self.w = w
		self.h = h
		self.mode = Scale.MODES[1]
		self.outW = w
		self.outH = h

	def generateArgsString(self):
		return str("{0}={1}:{2}".format(self.name, self.outW, self.outH))

class Setsar(Filter):
	# Set Sample Aspect Ratio
	# "setsar=1/1"
	MODES = [
		'value',
		'matchSource'
	]
	def __init__(self, sar='1/1'):
		Filter.__init__(self, "setsar")
		self.sar = sar
		self.mode = Setsar.MODES[1]
		self.outSar = sar

	def generateArgsString(self):
		return str("{0}={1}".format(self.name, self.outSar))

class Setdar(Filter):
	# Set Display Aspect Ratio
	# "setdar=1/1"
	MODES = [
		'value',
		'matchSource'
	]
	def __init__(self, dar='1/1'):
		Filter.__init__(self, "satdar")
		self.dar = dar
		self.mode = Setdar.MODES[1]
		self.outDar = dar

	def generateArgsString(self):
		return str("{0}={1}".format(self.name, self.outDar))

class Stereo3d(Filter):
	# Modify a single stream stereo format
	# "stereo3d=sbsl:abl"

	STEREOFORMATS = [
		"sbsl",				#side by side parallel (left eye left, right eye right)
		"sbsr",				#side by side crosseye (right eye left, left eye right)
		"sbs2l",			#side by side parallel with half width resolution (left eye left, right eye right)
		"sbs2r",			#side by side crosseye with half width resolution (right eye left, left eye right)
		"abl",				#above-below (left eye above, right eye below)
		"abr",				#above-below (right eye above, left eye below)
		"ab2l",				#above-below with half height resolution (left eye above, right eye below)
		"ab2r",				#above-below with half height resolution (right eye above, left eye below)
		"ml",					#mono output (left eye only)
		"mr",					#mono output (right eye only)
	]
	MODES_IN = [
		"sbsl",
		"abl",
	]
	MODES_OUT = [
		"sbsl",
		"abl",
		"ml",
		"mr",
	]

	def __init__(self, inFormat='ml', outFormat='ml'):
		Filter.__init__(self, "stereo3d")
		self.inFormat = inFormat
		self.outFormat = outFormat

	def setOutMono(self):
		self.outFormat = "ml"
	def setInSBS(self):
		self.inFormat = "sbsl"
	def setOutSBS(self):
		self.outFormat = "sbsl"
	def setInTB(self):
		self.inFormat = "abl"
	def setOutTB(self):
		self.outFormat = "abl"

	def generateArgsString(self):
		return str("{0}={1}:{2}".format(self.name, self.inFormat, self.outFormat))

class Hstack(Filter):
	# Stack input videos horizontally(res is added)
	# All streams must be of same pixel format and of same height
	def __init__(self):
		Filter.__init__(self, "hstack")

class Vstack(Filter):
	# Stack input videos vertically(res is added)
	# All streams must be of same pixel format and of same width
	def __init__(self):
		Filter.__init__(self, "vstack")

###########
# OUTPUTS #
###########
class Output:
	CODECS = [
		"prores_ks",
		"libx264",
	]
	PRO_RES_PIX_FMT = [
		"yuv420p",
		"yuv422p10le",
		"yuva444p10le",
	]
	PRO_RES_PROFILES= [
		"proxy",
		"lt",
		"standard",
		"hq",
		"4444",
	]
	CODECS_PRESETS = [
		"prores_proxy",
		"prores_lt",
		"prores_standard",
		"prores_hq",
		"prores_4444",
		"h264_CRF_medium",
		"h264_CRF_fast",
		"h264_CBR_60_Kbps",
		"h264_CBR_40_Kbps",
	]

	def __init__(self, url, preset="prores_hq"):
		self.url = os.path.splitext(url)[0]
		self.preset = preset
		self.qscale = 5
		self.fps = ""

	def getExtString(self):
		return ".mov" if "prores" in self.preset else ".mp4"

	def getFpsString(self):
		return "-r "+ str(self.fps)+" " if self.fps else ""

	def getFileNameString(self):
		return str(os.path.splitext(self.url)[0] + self.getExtString())

	def getShortUrl(self):
		drive, p = os.path.splitdrive(self.getFileNameString())
		head, tail = os.path.split(p)
		return  '{0}...{1}{2}'.format( drive, os.sep, tail)

	def	generateArgsList(self):
		if self.preset == "prores_proxy":
			return ['-c:v', 'prores_ks', '-profile:v', str(0), '-qscale:v', str(self.qscale), '-vendor', 'ap10',
						 '-pix_fmt', Output.PRO_RES_PIX_FMT[1], self.getFpsString(), self.getFileNameString()]
		elif self.preset == "prores_lt":
			return ['-c:v', 'prores_ks', '-profile:v', str(1), '-qscale:v', str(self.qscale), '-vendor', 'ap10',
						 '-pix_fmt', Output.PRO_RES_PIX_FMT[1], self.getFpsString(), self.getFileNameString()]
		elif self.preset == "prores_standard":
			return ['-c:v', 'prores_ks', '-profile:v', str(2), '-qscale:v', str(self.qscale), '-vendor', 'ap10',
						 '-pix_fmt', Output.PRO_RES_PIX_FMT[1], self.getFpsString(), self.getFileNameString()]
		elif self.preset == "prores_hq":
			return ['-c:v', 'prores_ks', '-profile:v', str(3), '-qscale:v', str(self.qscale), '-vendor', 'ap10',
						 '-pix_fmt', Output.PRO_RES_PIX_FMT[1], self.getFpsString(), self.getFileNameString()]
		elif self.preset == "prores_4444":
			return ['-c:v', 'prores_ks', '-profile:v', str(4), '-qscale:v', str(self.qscale), '-vendor', 'ap10',
						 '-pix_fmt', Output.PRO_RES_PIX_FMT[2], self.getFpsString(), self.getFileNameString()]
		elif self.preset == "h264_CRF_fast":
			return ['-c:v', 'libx264', '-profile:v', 'main', '-preset', 'fast', '-pix_fmt',
							Output.PRO_RES_PIX_FMT[0], self.getFpsString(), self.getFileNameString()]
		elif self.preset == "h264_CRF_medium":
			return ['-c:v', 'libx264', '-profile:v', 'main', '-preset', 'medium', '-pix_fmt',
							Output.PRO_RES_PIX_FMT[0], self.getFpsString(), self.getFileNameString()]
		elif self.preset == "h264_CBR_40_Kbps":
			return ['-c:v', 'libx264', '-profile:v', 'main', '-crf', str(16), '-maxrate',
							str(40)+'M', '-bufsize', str(2)+'M', '-pix_fmt', Output.PRO_RES_PIX_FMT[0],
							self.getFpsString(), self.getFileNameString()]
		elif self.preset == "h264_CBR_60_Kbps":
			return ['-c:v', 'libx264', '-profile:v', 'main', '-crf', str(16), '-maxrate',
							str(60)+'M', '-bufsize', str(3)+'M', '-pix_fmt', Output.PRO_RES_PIX_FMT[0],
							self.getFpsString(), self.getFileNameString()]

	def generateArgsString(self):
		return " ".join(self.generateArgsList())

		"""
		prores
		-qscale:v 5  0(best) to 32(worst)

		h264

		CRF:
		This method allows the encoder to attempt to achieve a certain output quality
		for the whole file when output file size is of less importance.
		0-51: where 0 is lossless, 23 is default, and 51 is worst possible

		presets:
		ultrafast,superfast, veryfast, faster, fast, medium, slow, slower, veryslow, placebo

		According the x264 developer's blog you set:
		vbv-maxrate = bitrate = B = target bitrate
		vbv-bufsize = B / fps (in this video's case that's 24 fps)

		-crf 23 -maxrate 1M -bufsize 2M
		"""

class Ffmpeg:
	SIMPLE_FITLERS = [
		Scale,
		Setsar,
		Setdar,
		Stereo3d,
	]
	COMPLEX_FITLERS = [
		Hstack,
		Vstack,
	]
	OUT_STEREO_TYPES = [
		'mono',
		'SBS',
		'TB',
	]
	def __init__(self):
		self.baseArgs = [
			"ffmpeg",
			"-y",												# force overwrite output. Inverse is "-n"
		]
		self.simpleFiltersBaseArgs = [ # "," to chain
			"-filter:v",
		]
		self.complexFiltersBaseArgs = [ # "," to chain, ";" to new chain. Specify [in][out][0/1] (can create custom tag)
			"-filter_complex:v",
		]
		self.inputs = []
		self.simpleFilters = []
		self.complexFilters = []
		self.outputs = []
		self.outW = 0
		self.outH = 0
		self.outSar = '1/1'
		self.outDar = '1/1'
		self.outStereoType = Ffmpeg.OUT_STEREO_TYPES[0]

	def addInput(self, i):
		self.inputs.append(i)
		self.SetRes()

	def addFilter(self, f):
		if [i for i in Ffmpeg.COMPLEX_FITLERS if isinstance(f, i)]:
			self.complexFilters.append(f)
		else:
			self.simpleFilters.append(f)
			self.SetRes()

	def setStereoType(self, t):
		self.outStereoType = t

	def SetRes(self):
		if self.simpleFilters and self.inputs:
			i = self.inputs[0]
			for f in self.simpleFilters:
				if isinstance(f, Scale):
					w = 0
					h = 0
					if f.mode == Scale.MODES[0]:		# values
						w = f.w
						h = f.h
					elif f.mode == Scale.MODES[1]:	# matchSource
						w = i.w
						h = i.h
					elif f.mode == Scale.MODES[2]:	# halfSource
						w = int(round(float(i.w)/2))
						h = int(round(float(i.h)/2))
					elif f.mode == Scale.MODES[3]:	# halfWidthSource
						w = int(round(float(i.w)/2))
						h = i.h
					elif f.mode == Scale.MODES[4]:	# halfHeightSource
						w = i.w
						h = int(round(float(i.h)/2))
					self.outW = w
					self.outH = h
					f.outW = w
					f.outH = h

				if isinstance(f, Setsar):
					if f.mode == Setsar.MODES[0]:		# value
						self.outSar = f.sar
						f.outSar = f.sar
					if f.mode == Setsar.MODES[1]:		# matchSource
						self.outSar = i.sar
						f.outSar = i.sar

				if isinstance(f, Setdar):
					if f.mode == Setdar.MODES[0]:		# value
						self.outDar = f.dar
						f.outDar = f.dar
					if f.mode == Setdar.MODES[1]:		# matchSource
						self.outDar = i.dar
						f.outDar = i.dar

				if isinstance(f, Stereo3d):
					if "sb" in f.outFormat:
						self.outStereoType = Ffmpeg.OUT_STEREO_TYPES[1]
					elif "ab" in f.outFormat:
						self.outStereoType = Ffmpeg.OUT_STEREO_TYPES[2]
					else:
						self.outStereoType = Ffmpeg.OUT_STEREO_TYPES[0]

			for f in self.complexFilters:
				if isinstance(f, Hstack):
					self.outStereoType = Ffmpeg.OUT_STEREO_TYPES[1]
				elif isinstance(f, Vstack):
					self.outStereoType = Ffmpeg.OUT_STEREO_TYPES[2]

	def addOutput(self, o):
		self.outputs.append(o)
		self.SetRes()

	def genereateArgsList(self):
		FITLERS_ORDER = [
			Hstack,
			Vstack,
			Stereo3d,
			Scale,
			Setsar,
			Setdar,
		]
		args = []
		args.extend(self.baseArgs)
		# inputs
		if not self.inputs:
			raise ValueError("Ffmpeg needs at least one input")
		else:
			for i in self.inputs:
				args.extend(i.generateArgsList())
		# filters
		if not self.complexFilters:
			if self.simpleFilters:
				print("has simple filters")
				args.extend(self.simpleFiltersBaseArgs)
				args.append(",".join([f.generateArgsString() for f in self.simpleFilters]))
		else:
			# -filter_complex [0:v][1:v]vstack[oVstack];[oVstack]scale=1280:720[oScale];[oScale]setsar=1/1
			args.extend(self.complexFiltersBaseArgs)
			addedFilters = []
			addedFilters.extend(self.complexFilters)
			addedFilters.extend(self.simpleFilters)
			cfArgs = []
			tagI = 0
			inTag = ""
			outTag = ""
			for f in FITLERS_ORDER:
				for cf in addedFilters:
					if isinstance(cf, f):
						if tagI == 0:
							inTag = "".join(["[{0}:v]".format(i) for i in list(range(len(self.inputs)))])
							outTag = "[o{0}{1}]".format(cf.name, tagI)
						else:
							inTag = outTag
							outTag = "[o{0}{1}]".format(cf.name, tagI)
						if tagI >= len(addedFilters)-1:
							outTag = ""
						print(cf.generateArgsString(), type(cf.generateArgsString()))
						print("inTag: ", inTag)
						print("outTag: ", outTag)
						print(inTag+cf.generateArgsString()+outTag)
						cfArgs.append(str(inTag+cf.generateArgsString()+outTag))
						tagI +=1
			args.append(";".join(cfArgs))
		#outputs
		if not self.outputs:
			raise ValueError("Ffmpeg needs at least one output")
		else:
			for i in self.outputs:
				args.extend(i.generateArgsList())

		return [a for a in args if not (a.isspace() or a == '') ]

	def genereateArgsString(self):
		return " ".join(self.genereateArgsList())

	def run(self):
		cmdList = self.genereateArgsList()
		print("Ffmpeg.run(): ", cmdList)
		subprocess.call(cmdList)

	def inputSummary(self, idx=None):
		if self.inputs:
			result = []
			if idx ==None:
				for i in self.inputs:
					result.append(i.summary())
			else:
				result.append(self.inputs[idx])
			return '\n\n'.join(result)
		else:
			return "No input."

	def outputSummary(self, idx=None):
		inputs = True if self.inputs else False
		outputs = True if self.outputs else False

		def indivSummary(i, o):
			return '{0}\n{1}x{2} ({3}), {4} fps\n{5}, {6} frames\nview: {7}'.format(
				o.getShortUrl(), self.outW, self.outH, self.outSar, i.getFramerateString(),
				i.getDuration(), i.getFramesCount(), self.outStereoType)

		if inputs and outputs:
			firstInput = self.inputs[0]
			result = []
			if idx == None:
				for output in self.outputs:
					result.append(indivSummary(firstInput, output))
			else:
				result.append(indivSummary(firstInput, self.outputs[idx]))
			return '\n\n'.join(result)
		else:
			st = ''
			if not inputs:
				st += 'No input.'
			if not outputs:
				st += ' No output.'
			return st

if __name__ == "__main__":
	print("ffmpeg")

	seq = r"Z:\Programming\Python\ffmpeg\sources\fish\fish.%07d.tif"
	video = r"Z:\Programming\Python\ffmpeg\sources\fish_stereo_output.mov"
	left = r'Z:\Programming\Python\ffmpeg\sources\fish_stereo\fish_left.%07d.tif'
	right = r'Z:\Programming\Python\ffmpeg\sources\fish_stereo\fish_right.%07d.tif'
	start = 1
	end = 10


	ff = Ffmpeg()
	#inputs
	inputA = Input(video)
	inputA.setFramerate(30)
	ff.addInput(inputA)

	inputB = Input(video)
	inputB.setFramerate(30)
	ff.addInput(inputB)

	#filters
	#fHstack = Hstack()
	#ff.addFilter(fHstack)

	fVstack = Vstack()
	ff.addFilter(fVstack)

	"""
	fStereo3d = Stereo3d()
	fStereo3d.setInSBS()
	fStereo3d.setOutMono()
	ff.addFilter(fStereo3d)
	"""

	fScale = Scale(500,500)
	fScale.mode = Scale.MODES[4]
	ff.addFilter(fScale)

	fSetsar = Setsar('2/1')
	#fSetsar.mode = Setsar.MODES[0]
	ff.addFilter(fSetsar)
	#outputs
	oa = Output(r"Z:\Programming\Python\ffmpeg\sources\fish_test_v009.mov")
	oa.preset = "prores_4444"
	ff.addOutput(oa)
	pprint.pprint(ff.genereateArgsList())

	print("\ninput:")
	print(ff.inputSummary())
	print("\noutput:")
	print(ff.outputSummary())
	ff.run()
	print("\noutput:")
	print(ff.outputSummary())
	# python Z:\Programming\Python\ffmpeg\ffmpeg.py
	# C:\Python27\python.exe Z:\Programming\Python\ffmpeg\ffmpeg.py

