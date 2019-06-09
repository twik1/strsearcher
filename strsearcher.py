import argparse
import os
import re
import sys
import threading
import mmap
import codecs

enc = 'utf-8'
threads = 5

#class Counter:
#    def __init__(self):
#        self.files = 0
#        self.strings = 0
#        self.time

# Global instance should have locks
class ThreadClassHandler:
    def __init__(self, size, file):
        self.sem = threading.Semaphore(size)
        self.threads = [0] * size
        self.file = file
        self.locki = threading.Lock()
        self.lockw = threading.Lock()

    def enter(self, obj):
        self.sem.acquire()
        self.locki.acquire()
        for index in range(len(self.threads)):
            if self.threads[index] == 0:
                self.threads.insert(index, obj)
                break
            else:
                pass
        self.locki.release()

    def leave(self, obj):
        self.locki.acquire()
        for index in range(len(self.threads)):
            if self.threads[index] == obj:
                self.threads.insert(index, 0)
                self.sem.release()
                break
            else:
                pass
        self.locki.release()

    def threadjoin(self):
        self.locki.acquire()
        for index in range(len(self.threads)):
            if not self.threads[index] == 0:
                self.threads[index].join()
        self.locki.release()

    def thread_safe_output(self, msg):
        self.lockw.acquire()
        if self.file:
            self.file.write('{}\n'.format(msg))
        self.lockw.release()

def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper

class StrObj:
    def __init__(self, filename, handler, patternobj, patternobjpwd):
        if not os.path.exists(filename):
            self.exist = False
            print('File doesnt exist')
            return None
        self.exist = True
        self.size = os.path.getsize(filename)
        self.filename = filename
        self.index = 0
        self.handler = handler
        self.patternobj = patternobj
        self.patternobjpwd = patternobjpwd
        self.work = threading.Thread.__init__(self)
        #print('firing up {}'.format(self.filename))
        return None

    @threaded
    def strsearch(self, size, obj):
        leftover = self.size
        #print('leftover {}'.format(leftover))
        try:
            with open(self.filename, 'r', encoding=enc, ) as self.f:
                with mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ) as self.m:
                    while leftover > 0:
                        buffer = codecs.decode(self.m.read(size), enc, errors='ignore')
                        matchlist = self.patternobj.findall(buffer)
                        for match in matchlist:
                            if len(match) >= int(flags['low']) and len(match) <= int(flags['top']):
                                if self.patternobjpwd:
                                    if not self.patternobjpwd.match(match):
                                        continue
                                if 'out' in flags:
                                    self.handler.thread_safe_output(match)
                                else:
                                    print(match)

                        leftover -= size
        #print('leaving {}'.format(self.filename))
        except:
            print('unable to open {}'.format(self.filename))
        self.handler.leave(obj)

    def get_status(self):
        proc = (self.index/self.size)*100
        return {'filename':self.filename, '%': proc}

def query_yes_no(question, default="yes"):
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


if __name__ == '__main__':
    privesc_parameter = {}
    parser = argparse.ArgumentParser(description='StrSearcher v0.2')
    parser.add_argument('-t', '--top', help='Max number of characters to search for, 10 default', required=False)
    parser.add_argument('-l', '--low', help='Min number of characters to search for, 3 default', required=False)
    parser.add_argument('-s', '--spec', help='Serach for special characters too', action='store_true', required=False)
    parser.add_argument('-r', '--reg', help='Add your own regular expression to search for text', required=False)
    parser.add_argument('-p', '--pwd', help='Add your own second regular expression with password rules', required=False)
    parser.add_argument('-e', '--enc', help='Add your own encoding, default encoding = utf-8', required=False)
    parser.add_argument('-o', '--out', help='Output file, if no output file it goes to stdout', required=False)
    parser.add_argument('-i', '--indir', help='Dir to search in', required=True)

    args = parser.parse_args()

    flags = {}
    if args.top:
        flags['top'] = args.top
    else:
        flags['top'] = '10'
    if args.low:
        flags['low'] = args.low
    else:
        flags['low'] = '3'
    if args.spec:
        flags['spec'] = args.spec
    if args.pwd:
        flags['pwd'] = args.pwd
    if args.out:
        flags['out'] = args.out
    if args.enc:
        flags['enc'] = args.enc
    if args.reg:
        flags['reg'] = args.reg
    flags['indir'] = args.indir

    # Sanity check the arguments
    # Does the indir exist?
    if not os.path.exists(flags['indir']):
        print('{} Doesn\'t exist!'.format(flags['indir']))
        exit(1)
    # Number to search for
    if int(flags['low']) < 3:
        print('Not relevant to search for strings with less then 3 characters')
        exit(1)
    if int(flags['low']) > int(flags['top']):
        print('Hey you are mixing -t and -l up here!')
        exit(1)
    if 'out' in flags:
        if os.path.exists(flags['out']):
            run = query_yes_no('{} Already exist, overwrite?'.format(flags['out']))
            if not run:
                exit(1)
        try:
            file = open(flags['out'], 'w')
        except IOError:
            print('Unable to open output file: {}'.format(flags['out']))
            exit(1)
    else:
        file = None
    if 'enc' in flags:
        try:
            tststr = 'teststring'
            testcode = tststr.encode(flags['enc'], 'strict')
            enc = flags['enc']
        except:
            print('Unknown encoding: {}'.format(flags['enc']))
            exit(1)
    else:
        enc = "utf-8"

    # Pattern
    if 'reg' in flags:
        try:
            patternobj = re.compile(flags['reg'])
        except:
            print('Syntax problems with your regular expression')
            exit(1)
    else:
        if 'spec' in flags:
            patternobj = re.compile('[a-zA-Z0-9" \-!"#$%&\'()*+,./:;<=>?@[^_{|}~\"åäöÅÄÖ]+')
        else:
            patternobj = re.compile('[a-zA-Z0-9 +\-,.:;?]+')

    if 'pwd' in flags:
        try:
            patternobjpwd = re.compile(flags['pwd'])
        except:
            print('Syntax problems with your password regular expression')
            exit(1)
    else:
        patternobjpwd = None


    handler = ThreadClassHandler(threads, file)

    # Do the search
    for parent, dirnames, filenames in os.walk(flags['indir']):
        for fn in filenames:
            filepath = os.path.join(parent, fn)
            obj = StrObj(filepath, handler, patternobj, patternobjpwd)
            handler.enter(obj)
            obj.strsearch(1000, obj)

    # When about to leave make sure all thread are terminated first
    handler.threadjoin()



