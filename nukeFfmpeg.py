import nuke
import nukescripts
import ffmpeg
import re
import quickSeq

class FFmpegPanel(nukescripts.PythonPanel):

	STEREO_KNOBS = [
		'fileRight',
		'summaryRight',
		'StereoMerge',
	]
	STEREO_KNOBS_INV = [
		'enableStereoConvertTitle',
		'enableStereoConvert',
		'StereoIn',
		'StereoOut',
	]
	STEREO_CONVERT_KNOBS = [
		'StereoIn',
		'StereoOut',
	]
	SECOND_OUTPUT_KNOB = [
		'fileOutput2',
		'codecPreset2',
		'summaryOuput2',
	]
	CHUNKS_KNOBS = [
		'chunckVal',
		'chunkSecs',
	]
	def __init__(self):
		nukescripts.PythonPanel.__init__(self, 'FFmpeg Panel')
		print("FFmpeg Panel")
		self.canShow = True
		self.createKnobs()
		self.setKnobsFlags()
		self.setKnobsDefaults()
		self.setMinimumSize(700, 800)
		self.inputs = []
		self.inputsFromSelected()
		self.outputs = []

		print(self.inputs)

		if self.canShow:
			self.showPanel()

	def createKnobs(self):
		self.knobsList = []
		self.knobsList.append(nuke.Text_Knob("inputsGrp", 'Input 																							'))
		self.knobsList.append(nuke.File_Knob('fileLeft', 'Main /Left'))
		self.knobsList.append(nuke.Text_Knob("summaryLeft","Summary:", '\n\n\n\n'))
		self.knobsList.append(nuke.Boolean_Knob('enableStereoInputs', 'Stereo Input'))
		self.knobsList.append(nuke.File_Knob('fileRight', 'Right'))
		self.knobsList.append(nuke.Text_Knob("summaryRight","Summary:", '\n\n\n\n'))
		self.knobsList.append(nuke.Text_Knob("FiltersGrp", 'Filters 																							'))
		self.knobsList.append(nuke.Enumeration_Knob("StereoMerge", 'Stereo Merge', ["SBS", "TB"]))
		self.knobsList.append(nuke.Text_Knob('enableStereoConvertTitle', 'Stereo Convert', ' '))
		self.knobsList.append(nuke.Boolean_Knob('enableStereoConvert', ''))
		self.knobsList.append(nuke.Enumeration_Knob("StereoIn", '    Input ', ffmpeg.Stereo3d.MODES_IN))
		self.knobsList.append(nuke.Enumeration_Knob("StereoOut", '    Output', ffmpeg.Stereo3d.MODES_OUT))
		self.knobsList.append(nuke.Enumeration_Knob("sarType", 'Sample Aspect Ratio', ffmpeg.Setsar.MODES))
		self.knobsList.append(nuke.Double_Knob("sarVal", ''))
		self.knobsList.append(nuke.Enumeration_Knob("scaleType", 'Output Resolution', ffmpeg.Scale.MODES))
		self.knobsList.append(nuke.Double_Knob("scaleW", ''))
		self.knobsList.append(nuke.Double_Knob("scaleH", ''))
		self.knobsList.append(nuke.Text_Knob("outputsGrp", 'Output 																							'))
		self.knobsList.append(nuke.File_Knob('fileOutput1', 'Output'))
		self.knobsList.append(nuke.Enumeration_Knob("codecPreset1", '    Codec Preset ', ffmpeg.Output.CODECS_PRESETS))
		self.knobsList.append(nuke.Text_Knob("summaryOuput1","Summary:", '\n\n\n\n'))
		self.knobsList.append(nuke.Boolean_Knob('enableSecondOutput', 'Second'))
		self.knobsList.append(nuke.File_Knob('fileOutput2', 'Output'))
		self.knobsList.append(nuke.Enumeration_Knob("codecPreset2", '    Codec Preset ', ffmpeg.Output.CODECS_PRESETS))
		self.knobsList.append(nuke.Text_Knob("summaryOuput2","Summary:", '\n\n\n\n'))
		self.knobsList.append(nuke.Text_Knob("ChucksGrp", 'Chunks 																							'))
		self.knobsList.append(nuke.Text_Knob('enableStereoChunksTitle', 'enable', ' '))
		self.knobsList.append(nuke.Boolean_Knob('enableChunks', ''))
		self.knobsList.append(nuke.Double_Knob("chunckVal", '       each'))
		self.knobsList.append(nuke.Text_Knob('chunkSecs', '', 'Seconds'))
		self.knobsList.append(nuke.Text_Knob(""))
		self.knobsList.append(nuke.Text_Knob("console", "Console:", " "))

		for k in self.knobsList:
			self.addKnob(k)

	def stop(self, message):
			nuke.message(message)
			self.canShow = False

	def inputsFromSelected(self):
		sel = nuke.selectedNodes('Read')
		if len(sel) > 2:
			self.stop('FFmpeg: Too many reads selected. ({0}/{1})'.format(len(sel), 2))
		mono = []
		left = []
		right = []
		stereo = []
		for n in sel:
			print("eval: ", n.knob('file').evaluate())
			#print("lol: ", nuke.tcl(n.knob('file').value()))
			try:
				s = quickSeq.Seq(n.knob('file').value())
				if s.viewType == quickSeq.URL_VIEW_TYPES[0]:
					mono.append(s)
				elif s.viewType == quickSeq.URL_VIEW_TYPES[1]:
					left.append(s)
				elif s.viewType == quickSeq.URL_VIEW_TYPES[2]:
					right.append(s)
				elif s.viewType == quickSeq.URL_VIEW_TYPES[3]:
					stereo.append(s)
			except:
				pass

		if len(stereo) > 1:
			self.stop('FFmpeg: Too many stereo reads selected. ({0}/{1})'.format(len(sel), 1))
		if len(mono) > 1:
			self.stop('FFmpeg: Too many mono reads selected. ({0}/{1})'.format(len(sel), 1))
		if len(left) > 1:
			self.stop('FFmpeg: Too many left reads selected. ({0}/{1})'.format(len(sel), 1))
		if len(right) > 1:
			self.stop('FFmpeg: Too many right reads selected. ({0}/{1})'.format(len(sel), 1))
		if stereo:
			self.inputs.extend(stereo)
			return
		if right:
			self.inputs.extend(right)
		if left:
			self.inputs.extend(left)
			if right:
				self.inputs.reverse()
				return
		if mono:
			self.inputs.extend(mono)
			if right:
				self.inputs.reverse()


	def setKnobsDefaults(self):
		self.getKnob('sarType').setValue(ffmpeg.Setsar.MODES[1])
		self.getKnob('sarVal').setValue(1)
		self.getKnob('scaleType').setValue(ffmpeg.Scale.MODES[1])
		self.getKnob('scaleW').setValue(4096)
		self.getKnob('scaleH').setValue(2048)
		self.getKnob('codecPreset1').setValue(ffmpeg.Output.CODECS_PRESETS[3])
		self.getKnob('codecPreset2').setValue(ffmpeg.Output.CODECS_PRESETS[7])
		self.getKnob('chunckVal').setValue(5)
		self.getKnob('enableChunks').setValue(True)

	def setKnobsFlags(self):
		for k in FFmpegPanel.STEREO_KNOBS:
			self.getKnob(k).setVisible(False)

		for k in FFmpegPanel.STEREO_CONVERT_KNOBS:
			self.getKnob(k).setVisible(False)

		for k in FFmpegPanel.SECOND_OUTPUT_KNOB:
			self.getKnob(k).setVisible(False)

		# default values
		self.getKnob('summaryLeft').setEnabled(False)
		self.getKnob('summaryRight').setEnabled(False)
		self.getKnob('sarVal').setVisible(False)
		self.getKnob('enableStereoConvertTitle').clearFlag(nuke.ENDLINE )
		self.getKnob('enableStereoConvert').clearFlag(nuke.STARTLINE )
		self.getKnob('StereoIn').clearFlag(nuke.STARTLINE )
		self.getKnob('StereoOut').clearFlag(nuke.STARTLINE )
		self.getKnob('sarVal').setVisible(False)
		self.getKnob('sarVal').clearFlag(nuke.STARTLINE )
		self.getKnob('sarVal').clearFlag(0x00000002)# remove slider
		self.getKnob('scaleW').clearFlag(nuke.STARTLINE )
		self.getKnob('scaleW').clearFlag(0x00000002)# remove slider
		self.getKnob('scaleH').clearFlag(nuke.STARTLINE )
		self.getKnob('scaleH').clearFlag(0x00000002)# remove slider
		self.getKnob('scaleW').setVisible(False)
		self.getKnob('scaleH').setVisible(False)
		self.getKnob('enableStereoChunksTitle').clearFlag(nuke.ENDLINE )
		self.getKnob('enableChunks').clearFlag(nuke.STARTLINE )
		self.getKnob('chunckVal').clearFlag(nuke.STARTLINE )
		self.getKnob('chunckVal').clearFlag(0x00000002)# remove slider
		self.getKnob('chunkSecs').clearFlag(nuke.STARTLINE )

	def getKnob(self, k):
		return next(i for i in self.knobsList if i.name() == k )

	def knobChanged(self, knob):
		print("Knob Changed: ", knob.name())
		if knob.name() == 'enableStereoInputs':
			for k in FFmpegPanel.STEREO_KNOBS:
				obj = self.getKnob(k)
				if knob.value() == True:
					obj.setVisible(True)
				else:
					obj.setVisible(False)
			for k in FFmpegPanel.STEREO_KNOBS_INV:
				obj = self.getKnob(k)
				if knob.value() == False:
					if self.getKnob('enableStereoConvert').value() == True:
						obj.setVisible(True)
					else:
						self.getKnob('enableStereoConvertTitle').setVisible(True)
						self.getKnob('enableStereoConvert').setVisible(True)
				else:
					obj.setVisible(False)
		elif knob.name() == 'enableStereoConvert':
			for k in FFmpegPanel.STEREO_CONVERT_KNOBS:
				obj = self.getKnob(k)
				if knob.value() == True:
					obj.setVisible(True)
				else:
					obj.setVisible(False)
		elif knob.name() == 'sarType':
			obj = self.getKnob('sarType')
			if obj.value() == ffmpeg.Setsar.MODES[0]:
				self.getKnob('sarVal').setVisible(True)
			else:
				self.getKnob('sarVal').setVisible(False)
		elif knob.name() == 'scaleType':
			obj = self.getKnob('scaleType')
			if obj.value() == ffmpeg.Scale.MODES[0]:
				self.getKnob('scaleW').setVisible(True)
				self.getKnob('scaleH').setVisible(True)
			else:
				self.getKnob('scaleW').setVisible(False)
				self.getKnob('scaleH').setVisible(False)
		elif knob.name() == 'enableSecondOutput':
			for k in FFmpegPanel.SECOND_OUTPUT_KNOB:
				obj = self.getKnob(k)
				if knob.value() == True:
					obj.setVisible(True)
				else:
					obj.setVisible(False)
		elif knob.name() == 'enableChunks':
			for k in FFmpegPanel.CHUNKS_KNOBS:
				obj = self.getKnob(k)
				if knob.value() == True:
					obj.setVisible(True)
				else:
					obj.setVisible(False)

	def showPanel(self):
		self.showModalDialog()

# Result: ['_PythonPanel__node', '_PythonPanel__openTabGroups', '_PythonPanel__widget',
# '__class__', '__delattr__', '__dict__', '__doc__', '__format__', '__getattribute__',
# '__hash__', '__init__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__',
# '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_isModalDialog',
# '_makeOkCancelButton', 'accept', 'add', 'addCallback', 'addKnob', 'addToPane', 'cancel',
# 'cancelButton', 'close', 'create', 'destroy', 'finishModalDialog', 'height', 'hide',
# 'isEnabled', 'isValid', 'knobChanged', 'knobChangedCallback', 'knobs', 'ok', 'okButton',
# 'readKnobs', 'reject', 'removeCallback', 'removeKnob', 'setEnabled', 'setMaximumSize',
# 'setMinimumSize', 'setTooltip', 'setVisible', 'show', 'showModal', 'showModalDialog',
# 'tooltip', 'width', 'writeKnobs']