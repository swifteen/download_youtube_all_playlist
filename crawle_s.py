# -*- coding: utf-8 -*-

#import redis
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
import time
import threading
import traceback

import chardet
reload(sys)
sys.setdefaultencoding('utf-8')

#redis数据库key
ALL_TASK_KEY="youtube_all_task"
COMPLETE_TASK_KEY = "youtube_complete_task"

# Setting timeout
TIMEOUT = 10

# Retry times
RETRY = 5

# Medium Index Number that Starts from
START = 0

# Numbers of photos/videos per page
MEDIA_NUM = 50

# Numbers of downloading threads concurrently
THREADS = 20
web_mask = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Connection': 'keep-alive',
    'Host': 'ytube.win',
    # 'If-Range': '"5d6075a-7b50f8-568b00335adc6"',
    # 'Range': 'bytes=11353-11353',
    'Referer': 'http://ytube.win/',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
}

class ProgressBar(object):
    """
    链接：https://www.zhihu.com/question/41132103/answer/93438156
    来源：知乎
    """
    def __init__(self, title, count=0.0, run_status=None, fin_status=None, total=100.0, unit='', sep='/', chunk_size=1.0):
        super(ProgressBar, self).__init__()
        self.info = '\b' * 1024 + "【%s】     %s     %.2f %s %s %.2f %s"
        self.title = title
        self.total = total
        self.count = count
        self.chunk_size = chunk_size
        self.status = run_status or ""
        self.fin_status = fin_status or " " * len(self.statue)
        self.unit = unit
        self.seq = sep

    def __get_info(self):
        """【razorback】 下载完成 3751.50 KB / 3751.50 KB """
        _info = self.info % (self.title, self.status, self.count/self.chunk_size, self.unit, self.seq, self.total/self.chunk_size, self.unit)
        return _info

    def refresh(self, count=1, status=None):
        self.count += count
        self.status = status or self.status
        end_str = "\r"
        if self.count >= self.total:
            end_str = '\n'
            self.status = status or self.fin_status
        #print(self.__get_info(), end=end_str)
#       percent = float(size) / float(self.total) * 100
        sys.stdout.write(self.__get_info())
        sys.stdout.flush()
#       print(self.__get_info())

class DownloadWorker(Thread):

    def __init__(self, queue, cb_func):
        Thread.__init__(self)
        self.queue = queue
        self.total = 0
        self.size = 0
        self.filename = ''
        self.config = {
            'block': int(1024),
        }
        self.cb_func = cb_func

    def run(self):
        while True:
            title, hash_code, output_file_name, target_folder = self.queue.get()
            self.download(title, hash_code, output_file_name, target_folder)
            self.queue.task_done()

    def touch(self, filename):
        with open(filename, 'w') as fin:
            pass

    def remove_nonchars(self, name):
        (name, _) = re.subn(ur'[\\\/\:\*\?\"\<\>\|]', '', name)
        return name

    def support_continue(self, url):
        headers = {
            'Range': 'bytes=0-4'
        }
        try:
            r = requests.head(url, headers=headers)
            crange = r.headers['content-range']
            self.total = int(re.match(ur'^bytes 0-4/(\d+)$', crange).group(1))
            return True
        except:
            pass
        try:
            self.total = int(r.headers['content-length'])
        except:
            self.total = 0
        return False

    def sendRequest(self, title, hash_code, output_file_name):
        all_url = 'https://www.youtube.com/watch?v=' + hash_code
        all_url_b64 = base64.b64encode(all_url)
        payload = {
            'urlb64': all_url_b64,
        }
        res = requests.post(
            'http://fly.yescall.info/system/proceed.php', data=payload)
        soup = bs(res.text, "html5lib")
        # print soup
        if soup.a is None:
            return None
        remote_file_name = soup.a.string
        return remote_file_name

    def download(self, title, hash_code, output_file_name, target_folder):
        remote_file_name = self.sendRequest(title, hash_code, output_file_name)
        if not remote_file_name is None:
            mp4_url = 'http://ytube.win/cache/' + remote_file_name
            '''
            以下例子：
                第十四天05 敌机发射的子弹判断越界
                VdtjNjOZsdU
                202-05.mp4
            '''
            index = output_file_name.split('-')[0]
            new_title = re.sub(ur'[\\\/\:\*\?\"\<\>\|]', '_', title)
            file_suffix = remote_file_name.split('.')[1]
            file_name = index + '_' + new_title + '.' + file_suffix
            file_path = os.path.join(target_folder, file_name)
            file_path = os.path.join(target_folder, output_file_name)
            parent_path = os.path.dirname(file_path)
	    if not os.path.exists(parent_path):
                os.makedirs(parent_path)
            print "file_path is {} ,parent_path is {}".format(file_path, parent_path) 

            ret = self._download_file(mp4_url, file_path, hash_code)
            print "complete_task============="+ str(ret)
            if ret == 0:
        #保存完成，添加到已完成redis集合
                task = (title, hash_code, output_file_name, target_folder)
                complete_task = "#".join(task)
                print "complete_task============="+complete_task
		'''
                r = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)
                r.sadd(COMPLETE_TASK_KEY,complete_task)
		'''

    def _download_file(self, url, filename, hash_code, headers={}):
        finished = False
        block = self.config['block']
        local_filename = filename  # self.remove_nonchars(filename)
        tmp_filename = local_filename + '.downtmp'
        size = self.size
        #print local_filename
        #print tmp_filename

        if self.support_continue(url):  # 支持断点续传
            if os.path.exists(local_filename):
                tmp_size = os.path.getsize(local_filename)
                if self.total == tmp_size:
                    print "%s download success" % local_filename
                    return 0
                elif tmp_size > 0:
                    if not os.path.exists(tmp_filename):
                        with open(tmp_filename, 'wb') as ftmp:
                            ftmp.write(str(tmp_size / block * block))
                            ftmp.flush()
                    self.size = tmp_size / block * block
                    size = self.size + 1
                    print size
                    headers['Range'] = "bytes=%d-" % (self.size, )
                else:
                    pass
            else:
                try:
                    with open(tmp_filename, 'rb') as fin:
                        self.size = int(fin.read())
                        size = self.size + 1
                        print size
                except:
                    self.touch(tmp_filename)
                finally:
                    headers['Range'] = "bytes=%d-" % (self.size, )
                    print self.size
        else:
            self.touch(tmp_filename)
            self.touch(local_filename)
#创建进度条
        progress = ProgressBar(filename, total=self.total, unit="KB", chunk_size=block, run_status="正在下载", fin_status="下载完成")
#请求数据
        r = requests.get(url, data=web_mask, stream=True,
                         verify=False, headers=headers)
        start_t = time.time()
        with open(local_filename, 'ab+') as f:
            f.seek(self.size)
            f.truncate()
            try:
                download_t = time.time()
                for chunk in r.iter_content(chunk_size=block):
                    if chunk:
                        f.write(chunk)
                        size += len(chunk)

                        #刷新进度
                        progress.refresh(count=len(chunk))

                    if int(time.time() - download_t) >= 10:
                        download_t = time.time()

                        with open(tmp_filename, 'wb') as ftmp:
                            ftmp.write(str(size / block * block))
                            ftmp.flush()
                f.flush()
                finished = True
                os.remove(tmp_filename)
                return 0
            except:
                print "Download pause [%s] Total: %d Byte Temp: %d Byte" % (filename, self.total, size)
            finally:
                if not finished:
                    with open(tmp_filename, 'wb') as ftmp:
                        ftmp.write(str(size))
                        ftmp.flush()
                    return -1
                return 0


class CrawlerScheduler(object):

    def __init__(self):
        self.queue = Queue.Queue()
        self.lists = list()
        self.scheduling()
        self._value_lock = threading.Lock()

    def scheduling(self):
         # create workers
        for x in range(THREADS):
            worker = DownloadWorker(
                self.queue, self.write_uncomplete_list_file)
            # Setting daemon to True will let the main thread exit
            # even though the workers are blocking
            worker.daemon = True
            worker.start()

    def addTaskList(self, list):
        for task in list:
            self.queue.put(task)
        with self._value_lock:
            self.lists.extend(list)

    def taskComplete(self, hash_code):
        with self._value_lock:
            for task in self.lists:
                if task[1] == hash_code:
                    self.lists.remove(task)
                    self.write_uncomplete_list_file()
                    break

    def write_uncomplete_list_file(self):
        tmp_filename = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        print "write_uncomplete_list_file[%s]" % (tmp_filename)
        with open(tmp_filename + '.tmp', 'wb') as ftmp:
            for task in self.lists:
                one_file = task[0] + '\n' + task[1] + '\n' + task[2] + '\n'
                ftmp.write(str(one_file))
                ftmp.flush()


def usage():
    print(u"未找到list.txt文件，请创建.\n"
          u"第二个参数为列表文件，\n"
          u"第三个参数为导出目录名称,例如为[test],则最后的文件将下载到当前目录的test目录下，不填则以第二个参数的名称创建导出目录\n"
          u"例子: site1,site2\n\n"
          u"或者直接使用命令行参数指定站点\n"
          u"例子1: python crawle.py list.txt\n"
          u"例子2: python crawle.py list.txt test")


#解析任务列表文件
def parse_lists(filename, target_dir):
    target_folder = ""
    if "/" in target_dir:
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)
        target_folder = target_dir
    else:
        current_folder = os.getcwd()
        target_folder = os.path.join(current_folder, target_dir)
        if not os.path.isdir(target_folder):
            os.mkdir(target_folder)

    count = 0
    lists = list()
    title = ""
    hash_code = ""
    output_file_name = ""
    '''
    r = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)
    '''
    with open(filename, "r") as f:
        for line in f:
            raw_line = line.rstrip().lstrip()
            if count % 3 == 0:
                title = raw_line
            if count % 3 == 1:
                hash_code = raw_line
            if count % 3 == 2:
                output_file_name = raw_line
                task = (title, hash_code, output_file_name, target_folder)
                redis_element = "#".join(task)
                print "=============="+redis_element
		'''
                r.sadd(ALL_TASK_KEY,redis_element )
		'''
                lists.append(task)
            count += 1
    return lists


def tcplink(sock, addr, crawle):
    print 'Accept new connection from %s:%s...' % addr
    sock.send('Welcome!')
    data = None

    buffer = []
    while True:
        # 每次最多接收1k字节:
        d = sock.recv(1024)
        if d:
            buffer.append(d)
        else:
            break
    data = ''.join(buffer)
    sock.close()
    print 'Connection from %s:%s closed.' % addr

    filename, output_dir_name = data.split('#')
    print filename
    print output_dir_name
#解析任务列表文件
    lists = None
    if os.path.exists(filename):
        lists = parse_lists(filename, output_dir_name)
    if len(lists) == 0:
        usage()
        return
    crawle.addTaskList(lists)


if __name__ == "__main__":

    crawler = CrawlerScheduler()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', int(sys.argv[1])))
    s.listen(5)
    print 'Waiting for connection...'
    while True:
        # 接受一个新连接:
        sock, addr = s.accept()
        # 创建新线程来处理TCP连接:
        t = threading.Thread(target=tcplink, args=(sock, addr, crawler))
        t.start()
