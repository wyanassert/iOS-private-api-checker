#coding=utf-8
'''
Created on 2015年10月29日

@author: hzwangzhiwei
'''
import re
import os, time, datetime, random
import subprocess
from api import api_helpers
from dump import class_dump_utils
import zipfile

def unzip_ipa(ipa_path, dest_path):
    '''
    unzip a ipa, and return the zip folder
    '''
    file_zip = zipfile.ZipFile(ipa_path, 'r')
    for f in file_zip.namelist():
        file_zip.extract(f, dest_path)
    file_zip.close()
    return os.path.join(dest_path, 'Payload')

def get_executable_file(path):
    '''
    info:从ipa中解压出Payload目录中的xxx.app，扫描其中的文件，寻找 Mach-O 文件的路径
    '''
    for f in os.listdir(path):
        #TODO
        if f != '.DS_Store':
            path = os.path.join(path, f)
            break

    regex = re.compile(".*?Mach-O.*")
    for f in os.listdir(path):
        cmd = "file -b %s" % os.path.join(path, f)
        out = subprocess.check_output(cmd.split())
        if regex.search(out):
            return os.path.join(path, f)
    return None


def get_app_strings(app_path, pid):
    """
    Args:
        app : the full path of the Mach-O file in app
    Returns:
        outfile : the result file of the strings app
        
    info:strings - 显示文件中的可打印字符
    strings 的主要用途是确定非文本文件的包含的文本内容。
    """

    cmd = "/usr/bin/strings %s" % app_path
    output = subprocess.check_output(cmd.split())
    
    strings_file_name  = 'strings_' + os.path.basename(app_path) or 'strings'
    cur_dir = os.getcwd()
    if not os.path.isdir(os.path.join(cur_dir, "tmp")):
        os.makedirs(os.path.join(cur_dir, "tmp"))
    strings_file_name = os.path.join(cur_dir, "tmp/" + pid + '/' + strings_file_name)
    

    strings = open(strings_file_name + ".txt", "w")
    print >>strings, output #将strings内容输出到文件中
    return set(output.split())

def get_app_variables(app, pid):
    "get all variables, properties, and interface name"
    dump_result = class_dump_utils.dump_app(app)

    var_file_name  = 'dump_var_' + os.path.basename(app) or 'dump_var'
    cur_dir = os.getcwd()
    var_file_name = os.path.join(cur_dir, "tmp/" + pid + '/' + var_file_name)
    
    var_file = open(var_file_name + ".txt", "w")
    print >>var_file, dump_result #将strings内容输出到文件中

    interface = re.compile("^@interface (\w*).*")
    protocol = re.compile("@protocoli (\w*)")
    private = re.compile("^\s*[\w <>]* [*]?(\w*)[\[\]\d]*;")
    prop = re.compile("@property\([\w, ]*\) (?:\w+ )*[*]?(\w+); // @synthesize \w*(?:=([\w]*))?;")
    res = set()
    lines = dump_result.split("\n")
    wait_end = False 
    for line in lines:
        l = line.strip()
        if l.startswith("}"):
            wait_end = False
            continue
        if wait_end:
            r = private.search(l)
            if r:
                res.add(r.groups()[0])
            continue
        r = interface.search(l)
        if r:
            res.add(r.groups()[0])
            wait_end = True
            continue
        r = protocol.search(l)
        if r:
            res.add(r.groups()[0])
            wait_end = True
            continue
        r = prop.search(l)
        if r:
            m = r.groups()
            res.add(m[0])
            res.add("set" + m[0].title() + ":")
            #print "set" + m[0].title() + ":"
            if m[1] != None:
                # res.add("V"+m[1])
                res.add(m[1])
    return res


def get_app_methods(app, pid):
    '''
    info:获得app中的方法
    '''
    dump_result = class_dump_utils.dump_app(app)
    methods_file_name  = 'method_' + os.path.basename(app) or 'app_methods'
    cur_dir = os.getcwd()
    methods_file_name = os.path.join(cur_dir, "tmp/" + pid + '/' + methods_file_name)
    
    strings = open(methods_file_name + ".txt", "w")
    #print methods_file_name
    print >>strings, dump_result 
    #ret_methods = set()
    methods = api_helpers.extract(dump_result)
    #for m in methods:
    #    ret_methods = ret_methods.union(set(m["methods"]))
    #保留class_name信息
    return methods


def check_architectures(app):
    '''
    info检查是否支持64位
    demo:
    ljsg: Mach-O universal binary with 2 architectures
    ljsg (for architecture armv7):  Mach-O executable arm
    ljsg (for architecture arm64):  Mach-O 64-bit executable
    '''
    cmd = "file %s" % app
    output = subprocess.check_output(cmd.split())

    arcs = [] #architecture detail, eg: armv7, arm64

    lines = output.split("\n")
    arc_re = re.compile("\(for architecture (\w{1,})\)")
    for line in lines:
        r = arc_re.search(line)
        if r and len(r.groups()) > 0:
            arcs.append(r.groups()[0])

    return arcs


def get_unique_str():
    #随机的名字，可以用于上传文件等等不重复，但有一定时间意义的名字
    datetime_str = time.strftime('%Y%m%d%H%M%S',time.localtime())
    return datetime_str + str(datetime.datetime.now().microsecond / 1000) + str(random.randint(0, 1000))