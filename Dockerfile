ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

RUN apk add --no-cache \
    	jq \
        py-pip \
	python \
	python-dev \
	python3 \
	python3-dev\
 && pip install -U pip \
 && pip3 install -U pip \
 && pip install -U virtualenv \
 && pip3 install pyserial \
 && pip3 install paho-mqtt \
 && pip3 install tornado


# Copy data for add-on
COPY run.sh /
COPY MQTTClient.py /
COPY RFLinkGateway.py /
COPY SerialProcess.py /
COPY config.json /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
