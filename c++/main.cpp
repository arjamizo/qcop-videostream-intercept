#include <gst/gst.h>

/**
Works with
CLIENTIP=192.168.103 gst-launch-1.0 -v v4l2src ! timeoverlay shaded-background=true text="pi" ! video/x-raw,height=480,width=640,framerate=30/1 ! videoconvert ! omxh264enc ! rtph264pay ! udpsink host=$CLIENTIP port=5000
OR
http://wiki.oz9aec.net/index.php/Raspberry_Pi_Camera#Gstreamer_using_RTP.2FUDP
CLIENTIP=192.168.103 raspivid -n -w 1280 -h 720 -b 4500000 -fps 30 -vf -hf -t 0 -o - | \
	gst-launch-1.0 -v fdsrc !  h264parse ! rtph264pay config-interval=10 pt=96 ! \
	udpsink host=$CLIENTIP port=9000
sudo apt-get install libgstreamer1.0-dev
sudo apt-get install gstreamer1.0-libav
gst-launch-1.0 -v udpsrc port=9000 caps='application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264' ! \
     rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false
*/
#include <stdlib.h>
#include <stdio.h>
#define prexit(err) {printf(err " Error in line %d", __LINE__);exit(__LINE__%100);}
int main(int argc, char *argv[]) {

	putenv("GST_DEBUG=1");
	GstElement *pipeline;
	GstBus *bus;
	GstMessage *msg;
	GstStateChangeReturn r;

	/* Initialize GStreamer */
	gst_init (&argc, &argv);
	GError *error = NULL;
	/* Build the pipeline */

	//Compiling: g++ main.cpp `pkg-config --cflags --libs gstreamer-1.0 gtk+-2.0`; raspivid -n -t 1000000 -vf -b 2000000 -fps 25 -o - | GST_DEBUG=3 ./a.out
	//! x264enc pass=qual quantizer=20 tune=zerolatency
	pipeline = gst_parse_launch("fdsrc fd=0 ! h264parse ! rtph264pay config-interval=1 pt=96 ! gdppay ! udpsink host=192.168.0.104 port=1234", &error);
	//pipeline = gst_parse_launch("v4l2src device=/dev/video0 ! video/x-raw-yuv,width=640,height=480 ! x264enc pass=qual quantizer=20 tune=zerolatency ! rtph264pay ! udpsink host=127.0.0.1 port=1234", &error);
	//run
	//gst-launch-0* udpsrc port=1234 ! "application/x-rtp, payload=127" ! rtph264depay ! ffdec_h264 ! xvimagesink sync=false
	if (error) {
		printf ("Parse error: %p\n", error);
		exit (1);
	}
//	printf("ERROR %p %p", error, *error);
	/* Start playing */
	printf ("Starting playing: %p\n", r=gst_element_set_state (pipeline, GST_STATE_PLAYING));
	if(r==GST_STATE_CHANGE_FAILURE) prexit("Try sudo rmmod uvcvideo; sudo modprove uvcvideo");

	/* Wait until error or EOS */
	bus = gst_element_get_bus (pipeline);
	msg = gst_bus_timed_pop_filtered (bus, GST_CLOCK_TIME_NONE, (GstMessageType)(GST_MESSAGE_ERROR | GST_MESSAGE_EOS));

	/* Free resources */
	if (msg != NULL)
	gst_message_unref (msg);
	gst_object_unref (bus);
	gst_element_set_state (pipeline, GST_STATE_NULL);
	gst_object_unref (pipeline);
	return 0;
}
