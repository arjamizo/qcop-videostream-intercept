EXNAME = qreco-cb-prj
.PHONY: binDebug
all: bin/Debug/qreco-cb-prj
Debug: NAME = bin/Debug/
Debug: createFolder bin/Debug/qreco-cb-prj
createFolder:
	echo ${NAME}
	mkdir -p ${NAME}
bin/Debug/qreco-cb-prj: main.cpp
	ls .
	#opencv
	g++ main.cpp `pkg-config --cflags --libs gstreamer-1.0 gtk+-2.0` -o ${NAME}qreco-cb-prj
