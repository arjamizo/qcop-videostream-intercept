#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gst
import md5
import traceback
import cairo
from math import pi

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
		self.draw_on(outbuf)
		return self.srcpad.push(outbuf)
		
	def draw_on (self, buf):
		try:
			caps = buf.get_caps()
			width = caps[0]['width']
			height = caps[0]['height']
			framerate = caps[0]['framerate']
			width, height = width/2, height/2
			surface = cairo.ImageSurface.create_for_data (buf, cairo.FORMAT_ARGB32, width, height, 4 * width)
			ctx = cairo.Context(surface)
		except:
			print "Failed to create cairo surface for buffer"
			traceback.print_exc()
			return

		try:
			center_x = width/4
			center_y = 3*height/4

			# draw a circle
			radius = float (min (width, height)) * 0.25
			ctx.set_source_rgba (0.0, 0.0, 0.0, 0.9)
			ctx.move_to (center_x, center_y)
			ctx.arc (center_x, center_y, radius, 0, 2.0*pi)
			ctx.close_path()
			ctx.fill()
			ctx.set_source_rgba (1.0, 1.0, 1.0, 1.0)
			ctx.set_font_size(0.3 * radius)
			txt = "Hello World"
			extents = ctx.text_extents (txt)
			ctx.move_to(center_x - extents[2]/2, center_y + extents[3]/2)
			ctx.text_path(txt)
			ctx.fill()

		except:
			print "Failed cairo render"
			traceback.print_exc()

#here we register our class with glib, the c-based object system used by
#gstreamer
gobject.type_register(NewElement)

class GTK_Main:

	def __init__(self):
		window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		window.set_title("Intercepting web-cam")
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
		# src = gst.element_factory_make ("v4l2src")
		src = gst.element_factory_make ("videotestsrc")
		cf = gst.element_factory_make ("capsfilter")
		WIDTH, HEIGHT, FRAMERATE = 640, 480, 15
		caps = gst.caps_from_string ("video/x-raw-yuv,format=(fourcc)YUY2,width=%d,height=%d,framerate=%d/1" % (WIDTH, HEIGHT, FRAMERATE))
		cf.set_property ("caps", caps)
		filter = NewElement()
		sink = gst.element_factory_make('autovideosink')
		self.player.add(src, cf, filter, sink)
		gst.element_link_many(src, cf, filter, sink)

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