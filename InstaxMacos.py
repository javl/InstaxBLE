#!/usr/bin/env python3

class InstaxMacos:
    def send_packet(self, packet):
        raise NotImplementedError("send_packet not implemented for MacOS yet")

    def find_device(self, response):
        raise NotImplementedError("find_device not implemented for MacOS yet")

    def parse_response(self, response):
        raise NotImplementedError("parse_response not implemented for MacOS yet")
