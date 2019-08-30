# -*- coding: utf-8 -*-

import os
import sys
import requests
from six.moves import queue as Queue
from threading import Thread
import re
import json
import time
import urlparse
import shutil
import base64
from bs4 import BeautifulSoup as bs
import socket

def usage():
    print(u"未找到list.txt文件，请创建.\n"
          u"第二个参数为列表文件，\n"
          u"第三个参数为导出目录名称,例如为[test],则最后的文件将下载到当前目录的test目录下，不填则以第二个参数的名称创建导出目录\n"
          u"例子: site1,site2\n\n"
          u"或者直接使用命令行参数指定站点\n"
          u"例子1: python crawle.py list.txt\n"
          u"例子2: python crawle.py list.txt test")

if __name__ == "__main__":

    lists = None
    filename = None
    output_dir_name = None
    port = 0
    if len(sys.argv) == 3:
        filename = sys.argv[1]
        # output_dir_name = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        output_dir_name = os.path.basename(sys.argv[1]).split('.')[0]
        port = int(sys.argv[2])
    elif len(sys.argv) == 4:
        filename = sys.argv[1]
        output_dir_name = sys.argv[2]
	output_dir_name = os.path.abspath(sys.argv[2])
	print output_dir_name
        port = int(sys.argv[3])
    else:
        usage()
        sys.exit(1)
    data = filename + '#' + output_dir_name
    print data
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 建立连接:
    s.connect(('127.0.0.1', port))
    # 接收欢迎消息:
    print s.recv(1024)
    s.send(data)
    s.close()
