#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gst
import md5

class NewElement(gst.Element):
	""" A basic, buffer forwarding gstreamer element """

	#here we register our plugin details
	__gstdetails__ = (
		"NewElement plugin",
		"newelement.py",
		"gst.Element, that passes a buffer from source to sink (a filter)",
		"Stephen Griffiths <scgmk5@gmail.com>")
	
	#source pad (template): we send buffers forward through here
	_srctemplate = gst.PadTemplate ('src',
		gst.PAD_SRC,
		gst.PAD_ALWAYS,
		gst.caps_new_any())

	#sink pad (template): we recieve buffers from our sink pad
	_sinktemplate = gst.PadTemplate ('sink',
		gst.PAD_SINK,
		gst.PAD_ALWAYS,
		gst.caps_new_any())
	
	#register our pad templates
	__gsttemplates__ = (_srctemplate, _sinktemplate)

	def __init__(self, *args, **kwargs):   
		#initialise parent class
		gst.Element.__init__(self, *args, **kwargs)
		
		#source pad, outgoing data
		self.srcpad = gst.Pad(self._srctemplate)
		
		#sink pad, incoming data
		self.sinkpad = gst.Pad(self._sinktemplate)
		self.sinkpad.set_setcaps_function(self._sink_setcaps)
		self.sinkpad.set_chain_function(self._sink_chain)
		
		#make pads available
		self.add_pad(self.srcpad)
		self.add_pad(self.sinkpad)

	def _sink_setcaps(self, pad, caps):
		#we negotiate our capabilities here, this function is called
		#as autovideosink accepts anything, we just say yes we can handle the
		#incoming data
		return True

	def _sink_chain(self, pad, buf):
		print "filter", len(buf), md5.new(buf).hexdigest()
		#this is where we do filtering
		#and then push a buffer to the next element, returning a value saying
		# it was either successful or not.
		outbuf = buf.copy_on_write()
		return self.srcpad.push(outbuf)

#here we register our class with glib, the c-based object system used by
#gstreamer
gobject.type_register(NewElement)

class GTK_Main:

	def __init__(self):
		window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		window.set_title("Webcam-Viewer")
		window.set_default_size(500, 400)
		window.connect("destroy", gtk.main_quit, "WM destroy")
		vbox = gtk.VBox()
		window.add(vbox)
		self.movie_window = gtk.DrawingArea()
		vbox.add(self.movie_window)
		hbox = gtk.HBox()
		vbox.pack_start(hbox, False)
		hbox.set_border_width(10)
		hbox.pack_start(gtk.Label())
		self.button = gtk.Button("Start")
		self.button.connect("clicked", self.start_stop)
		hbox.pack_start(self.button, False)
		self.button2 = gtk.Button("Quit")
		self.button2.connect("clicked", self.exit)
		hbox.pack_start(self.button2, False)
		hbox.add(gtk.Label())
		window.show_all()

		# Set up the gstreamer pipeline
		self.player = gst.Pipeline("player")
		src = gst.element_factory_make("v4l2src", "camera")
		filter = NewElement()
		sink = gst.element_factory_make('autovideosink')
		self.player.add(src, filter, sink)
		gst.element_link_many(src, filter, sink)

		bus = self.player.get_bus()
		bus.add_signal_watch()
		bus.enable_sync_message_emission()
		bus.connect("message", self.on_message)
		bus.connect("sync-message::element", self.on_sync_message)

	def start_stop(self, w):
		if self.button.get_label() == "Start":
			self.button.set_label("Stop")
			self.player.set_state(gst.STATE_PLAYING)
		else:
			self.player.set_state(gst.STATE_NULL)
			self.button.set_label("Start")

	def exit(self, widget, data=None):
		gtk.main_quit()

	def on_message(self, bus, message):
		t = message.type
		if t == gst.MESSAGE_EOS:
			self.player.set_state(gst.STATE_NULL)
			self.button.set_label("Start")
		elif t == gst.MESSAGE_ERROR:
			err, debug = message.parse_error()
			print "Error: %s" % err, debug
			self.player.set_state(gst.STATE_NULL)
			self.button.set_label("Start")

	def on_sync_message(self, bus, message):
		if message.structure is None:
			return
		message_name = message.structure.get_name()
		if message_name == "prepare-xwindow-id":
			# Assign the viewport
			imagesink = message.src
			imagesink.set_property("force-aspect-ratio", True)
			imagesink.set_xwindow_id(self.movie_window.window.xid)

GTK_Main()
gtk.gdk.threads_init()
gtk.main()