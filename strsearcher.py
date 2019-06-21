import argparse
import os
import re
import sys
import threading
import mmap
import codecs
import time
import datetime

enc = 'utf-8'
threads = 5
chunksize = 1000

class ThreadClassHandler:
    """
    A class handling protecting common resources for threads.
    Also limiting the number of threads to what has been configured.
    """
    def __init__(self, size, file):
        self.sem = threading.Semaphore(size)
        self.threads = [0] * size
        self.file = file
        self.locki = threading.Lock()  # Lock protecting index
        self.lockw = threading.Lock()  # Lock protecting writing to output
        # Counters
        self.files = 0
        self.crossovers = 0
        self.foundstrings = 0

    def enter(self, obj):
        """
        Adding a string object to the list of available storage positions.
        If no storage position is available it blocks.
        :param obj:
        :return: Nothing
        """
        self.sem.acquire()
        self.locki.acquire()
        for index in range(len(self.threads)):
            if self.threads[index] == 0:
                self.threads[index] = obj
                #print('seize index:{}'.format(index))
                self.files += 1
                break
            else:
                pass
        self.locki.release()

    def leave(self, obj, foundstrings):
        """
        Removing the object from the a storage position.
        :param obj:
        :param foundstrings: Number of found strings for that object
        :return: Nothing
        """
        self.locki.acquire()
        self.foundstrings += foundstrings
        for index in range(len(self.threads)):
            if self.threads[index] == obj:
                self.threads[index] = 0
                self.sem.release()
                #print('leave index:{}'.format(index))
                break
            else:
                pass
        self.locki.release()

    def threadjoin(self):
        """
        Making sure all last threads are terminated before continuing
        :return: Nothing
        """
        threadlist = []
        self.locki.acquire()
        for index in range(len(self.threads)):
            if not self.threads[index] == 0:
                if self.threads[index].work.is_alive():
                    threadlist.append(self.threads[index].work)
        self.locki.release()
        # Release lock and join what's left
        for thread in threadlist:
            #print('joining thread:{}'.format(thread))
            thread.join()

    def thread_safe_output(self, msg):
        """
        Making sure output to file is exclusive to one thread at the time
        :param msg: Message to output
        :return: Nothing
        """
        self.lockw.acquire()
        if self.file:
            self.file.write('{}\n'.format(msg))
        self.lockw.release()

    def starttimer(self):
        """
        Starting the execution timer
        :return:
        """
        self.starttime = time.time()

    def endtimer(self):
        """
        Ending the execution timer
        :return:
        """
        self.stoptimer = time.time()

    def totaltime(self):
        """
        Returning the execution time
        :return: Execution time in seconds
        """
        if self.stoptimer and self.starttime:
            return self.stoptimer - self.starttime
        else:
            return 0

    def numoffiles(self):
        """
        Returning number of searched files
        :return: Number of searched files
        """
        return self.files


def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        #print('spwaning thred:{}'.format(thread))
        args[0].work = thread
        thread.start()
        return thread
    return wrapper

class StrObj:
    """
    A class with an instance of each file to search for strings in
    """
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
        self.work = 0
        self.patternobj = patternobj
        self.patternobjpwd = patternobjpwd
        self.foundstrings = 0

    @threaded
    def strsearch(self, size):
        """
        The string search function which will be run as a thread
        :param size: Size of chunks to split really large files to prevent memory exhaustion
        :return: Nothing
        """
        leftover = self.size
        # print('leftover {}'.format(leftover))
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
                                self.foundstrings += 1
                                if 'out' in flags:
                                    self.handler.thread_safe_output(match)
                                else:
                                    pass
                                    print(match)

                        leftover -= size
        #print('leaving {}'.format(self.filename))
        except:
            print('unable to open {}'.format(self.filename))
        self.handler.leave(self, self.foundstrings)

    def get_status(self):
        proc = (self.index/self.size)*100
        return {'filename': self.filename, '%': proc}


def query_yes_no(question, default="yes"):
    """
    Helper function for a user interaction yes/no
    :param question: Text to take position for with yes or no.
    :param default: Which answer will be if only return is pressed
    :return: True/False
    """
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
    #parser.add_argument('-r', '--reg', help='Add your own regular expression to search for text', required=False)
    parser.add_argument('-p', '--pwd', help='Add your own second regular expression with password rules', required=False)
    parser.add_argument('-e', '--enc', help='Add your own encoding, default encoding = utf-8', required=False)
    parser.add_argument('-o', '--out', help='Output file, if no output file it goes to stdout', required=False)
    parser.add_argument('-i', '--indir', help='Dir or file to search in', required=True)

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
#    if args.reg:
#        flags['reg'] = args.reg
    flags['indir'] = args.indir

    # Sanity check the arguments

    # Does the indir exist or is it a file?
    if os.path.isfile(flags['indir']):
        flags['file'] = True
    else:
        if not os.path.exists(flags['indir']):
            print('{} Doesn\'t exist!'.format(flags['indir']))
            exit(1)


    # Numbers to search for
    if int(flags['low']) < 3:
        print('Not relevant to search for strings with less then 3 characters')
        exit(1)
    if int(flags['low']) > int(flags['top']):
        print('Hey you are mixing -t and -l up here!')
        exit(1)

    # THe output file where all the strings will end up
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

    # The 'assumed' encoding, detafult is 'utf-8'
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

    # The second regular expression used to search for specific types of strings
    # Like password needs to include both lowercase and uppercase
    # Password needs to be a combination of numbers, letters and special chracters
    if 'pwd' in flags:
        try:
            patternobjpwd = re.compile(flags['pwd'])
        except:
            print('Syntax problems with your password regular expression')
            exit(1)
    else:
        patternobjpwd = None

    handler = ThreadClassHandler(threads, file)
    handler.starttimer()

    # Do the search
    if 'file' in flags:
        filepath = flags['indir']
        obj = StrObj(filepath, handler, patternobj, patternobjpwd)
        handler.enter(obj)
        obj.strsearch(chunksize)
    else:
        for parent, dirnames, filenames in os.walk(flags['indir']):
            for fn in filenames:
                filepath = os.path.join(parent, fn)
                obj = StrObj(filepath, handler, patternobj, patternobjpwd)
                handler.enter(obj)
                obj.strsearch(chunksize)
            pass
    pass

    # No more threads should be spawned
    # Let's collect whats left and join to make sure they are all done before continue
    handler.threadjoin()
    handler.endtimer()
    print('The search took {}s'.format(str(datetime.timedelta(seconds=handler.totaltime()))))
    print('I searched through {} files'.format(handler.numoffiles()))
    print('I found {} strings'.format(handler.foundstrings))
    print('All done!')

