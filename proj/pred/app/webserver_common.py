#!/usr/bin/env python

# Description:
#   A collection of classes and functions used by web-servers
#
# Author: Nanjiang Shu (nanjiang.shu@scilifelab.se)
#
# Address: Science for Life Laboratory Stockholm, Box 1031, 17121 Solna, Sweden

import os
import sys
import myfunc
import datetime
import time
import tabulate
import logging
import subprocess
def ReadProQ3GlobalScore(infile):#{{{
    #return globalscore and itemList
    #itemList is the name of the items
    globalscore = {}
    keys = []
    values = []
    try:
        fpin = open(infile, "r")
        lines = fpin.read().split("\n")
        fpin.close()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.lower().find("proq") != -1:
                keys = line.strip().split()
            elif myfunc.isnumeric(line.strip().split()[0]):
                values = line.split()
                try:
                    values = [float(x) for x in values]
                except:
                    values = []
        if len(keys) == len(values):
            for i in xrange(len(keys)):
                globalscore[keys[i]] = values[i]
    except IOError:
        pass
    return (globalscore, keys)
#}}}

def GetProQ3ScoreListFromGlobalScoreFile(globalscorefile):
    (globalscore, itemList) = ReadProQ3GlobalScore(globalscorefile)
    return itemList

def GetProQ3Option(query_para):#{{{
    """Return the proq3opt in list
    """
    yes_or_no_opt = {}
    for item in ['isDeepLearning', 'isRepack', 'isKeepFiles']:
        if query_para[item]:
            yes_or_no_opt[item] = "yes"
        else:
            yes_or_no_opt[item] = "no"

    proq3opt = [
            "-r", yes_or_no_opt['isRepack'],
            "-deep", yes_or_no_opt['isDeepLearning'],
            "-k", yes_or_no_opt['isKeepFiles'],
            "-quality", query_para['method_quality'],
            "-output_pdbs", "yes"         #always output PDB file (with proq3 written at the B-factor column)
            ]
    if 'targetlength' in query_para:
        proq3opt += ["-t", str(query_para['targetlength'])]

    return proq3opt

#}}}
def WriteSubconsTextResultFile(outfile, outpath_result, maplist,#{{{
        runtime_in_sec, base_www_url, statfile=""):
    try:
        fpout = open(outfile, "w")
        if statfile != "":
            fpstat = open(statfile, "w")

        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print >> fpout, "##############################################################################"
        print >> fpout, "Subcons result file"
        print >> fpout, "Generated from %s at %s"%(base_www_url, date)
        print >> fpout, "Total request time: %.1f seconds."%(runtime_in_sec)
        print >> fpout, "##############################################################################"
        cnt = 0
        for line in maplist:
            strs = line.split('\t')
            subfoldername = strs[0]
            length = int(strs[1])
            desp = strs[2]
            seq = strs[3]
            seqid = myfunc.GetSeqIDFromAnnotation(desp)
            print >> fpout, "Sequence number: %d"%(cnt+1)
            print >> fpout, "Sequence name: %s"%(desp)
            print >> fpout, "Sequence length: %d aa."%(length)
            print >> fpout, "Sequence:\n%s\n\n"%(seq)

            rstfile = "%s/%s/%s/query_0_final.csv"%(outpath_result, subfoldername, "plot")

            if os.path.exists(rstfile):
                content = myfunc.ReadFile(rstfile).strip()
                lines = content.split("\n")
                if len(lines) >= 6:
                    header_line = lines[0].split("\t")
                    if header_line[0].strip() == "":
                        header_line[0] = "Method"
                        header_line = [x.strip() for x in header_line]

                    data_line = []
                    for i in xrange(1, len(lines)):
                        strs1 = lines[i].split("\t")
                        strs1 = [x.strip() for x in strs1]
                        data_line.append(strs1)

                    content = tabulate.tabulate(data_line, header_line, 'plain')
            else:
                content = ""
            if content == "":
                content = "***No prediction could be produced with this method***"

            print >> fpout, "Prediction results:\n\n%s\n\n"%(content)

            print >> fpout, "##############################################################################"
            cnt += 1

    except IOError:
        print "Failed to write to file %s"%(outfile)
#}}}
def WriteProQ3TextResultFile(outfile, query_para, modelFileList, #{{{
        runtime_in_sec, base_www_url, proq3opt, statfile=""):
    try:
        fpout = open(outfile, "w")


        try:
            isDeepLearning = query_para['isDeepLearning']
        except KeyError:
            isDeepLearning = True

        if isDeepLearning:
            m_str = "proq3d"
        else:
            m_str = "proq3"

        try:
            method_quality = query_para['method_quality']
        except KeyError:
            method_quality = 'sscore'

        fpstat = None
        numTMPro = 0

        if statfile != "":
            fpstat = open(statfile, "w")
        numModel = len(modelFileList)

        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print >> fpout, "##############################################################################"
        print >> fpout, "# ProQ3 result file"
        print >> fpout, "# Generated from %s at %s"%(base_www_url, date)
        print >> fpout, "# Options for Proq3: %s"%(str(proq3opt))
        print >> fpout, "# Total request time: %.1f seconds."%(runtime_in_sec)
        print >> fpout, "# Number of finished models: %d"%(numModel)
        print >> fpout, "##############################################################################"
        print >> fpout
        print >> fpout, "# Global scores"
        fpout.write("# %10s"%("Model"))

        cnt = 0
        for i  in xrange(numModel):
            modelfile = modelFileList[i]
            globalscorefile = "%s.%s.%s.global"%(modelfile, m_str, method_quality)
            if not os.path.exists(globalscorefile):
                globalscorefile = "%s.proq3.%s.global"%(modelfile, method_quality)
                if not os.path.exists(globalscorefile):
                    globalscorefile = "%s.proq3.global"%(modelfile)
            (globalscore, itemList) = ReadProQ3GlobalScore(globalscorefile)
            if i == 0:
                for ss in itemList:
                    fpout.write(" %12s"%(ss))
                fpout.write("\n")

            try:
                if globalscore:
                    fpout.write("%2s %10s"%("", "model_%d"%(i)))
                    for jj in xrange(len(itemList)):
                        fpout.write(" %12f"%(globalscore[itemList[jj]]))
                    fpout.write("\n")
                else:
                    print >> fpout, "%2s %10s"%("", "model_%d"%(i))
            except:
                pass

        print >> fpout, "\n# Local scores"
        for i  in xrange(numModel):
            modelfile = modelFileList[i]
            localscorefile = "%s.%s.%s.local"%(modelfile, m_str, method_quality)
            if not os.path.exists(localscorefile):
                localscorefile = "%s.proq3.%s.local"%(modelfile, method_quality)
                if not os.path.exists(localscorefile):
                    localscorefile = "%s.proq3.local"%(modelfile)
            print >> fpout, "\n# Model %d"%(i)
            content = myfunc.ReadFile(localscorefile)
            print >> fpout, content

    except IOError:
        print "Failed to write to file %s"%(outfile)
#}}}

def GetLocDef(predfile):#{{{
    """
    Read in LocDef and its corresponding score from the subcons prediction file
    """
    content = ""
    if os.path.exists(predfile):
        content = myfunc.ReadFile(predfile)

    loc_def = None
    loc_def_score = None
    if content != "":
        lines = content.split("\n")
        if len(lines)>=2:
            strs0 = lines[0].split("\t")
            strs1 = lines[1].split("\t")
            strs0 = [x.strip() for x in strs0]
            strs1 = [x.strip() for x in strs1]
            if len(strs0) == len(strs1) and len(strs0) > 2:
                if strs0[1] == "LOC_DEF":
                    loc_def = strs1[1]
                    dt_score = {}
                    for i in xrange(2, len(strs0)):
                        dt_score[strs0[i]] = strs1[i]
                    if loc_def in dt_score:
                        loc_def_score = dt_score[loc_def]

    return (loc_def, loc_def_score)
#}}}
def IsFrontEndNode(base_www_url):#{{{
    """
    check if the base_www_url is front-end node
    if base_www_url is ip address, then not the front-end
    otherwise yes
    """
    base_www_url = base_www_url.lstrip("http://").lstrip("https://").split("/")[0]
    if base_www_url == "":
        return False
    elif base_www_url.find("computenode") != -1:
        return False
    else:
        arr =  [x.isdigit() for x in base_www_url.split('.')]
        if all(arr):
            return False
        else:
            return True
#}}}

def GetAverageNewRunTime(finished_seq_file, window=100):#{{{
    """Get average running time of the newrun tasks for the last x number of
sequences
    """
    logger = logging.getLogger(__name__)
    avg_newrun_time = -1.0
    if not os.path.exists(finished_seq_file):
        return avg_newrun_time
    else:
        indexmap_content = myfunc.ReadFile(finished_seq_file).split("\n")
        indexmap_content = indexmap_content[::-1]
        cnt = 0
        sum_run_time = 0.0
        for line in indexmap_content:
            strs = line.split("\t")
            if len(strs)>=7:
                source = strs[4]
                if source == "newrun":
                    try:
                        sum_run_time += float(strs[5])
                        cnt += 1
                    except:
                        logger.debug("bad format in finished_seq_file (%s) with line \"%s\""%(finished_seq_file, line))
                        pass

                if cnt >= window:
                    break

        if cnt > 0:
            avg_newrun_time = sum_run_time/float(cnt)
        return avg_newrun_time


#}}}
def GetRunTimeFromTimeFile(timefile, keyword=""):# {{{
    runtime = 0.0
    if os.path.exists(timefile):
        lines = myfunc.ReadFile(timefile).split("\n")
        for line in lines:
            if keyword == "" or (keyword != "" and line.find(keyword) != -1):
                ss2 = line.split(";")
                try:
                    runtime = float(ss2[1])
                    if keyword == "":
                        break
                except:
                    runtime = 0.0
                    pass
    return runtime
# }}}
def WriteDateTimeTagFile(outfile, runjob_logfile, runjob_errfile):# {{{
    if not os.path.exists(outfile):
        date_str = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            myfunc.WriteFile(date_str, outfile)
            msg = "Write tag file %s succeeded"%(outfile)
            myfunc.WriteFile("[%s] %s\n"%(date_str, msg),  runjob_logfile, "a", True)
        except Exception as e:
            msg = "Failed to write to file %s with message: \"%s\""%(outfile, str(e))
            myfunc.WriteFile("[%s] %s\n"%(date_str, msg),  runjob_errfile, "a", True)
# }}}
def RunCmd(cmd, runjob_logfile, runjob_errfile):# {{{
    """Input cmd in list
       Run the command and also output message to logs
    """
    begin_time = time.time()

    cmdline = " ".join(cmd)
    date_str = time.strftime("%Y-%m-%d %H:%M:%S")
    msg = "cmdline: %s"%(cmdline)
    myfunc.WriteFile("[%s] %s\n"%(date_str, msg),  runjob_logfile, "a", True)
    rmsg = ""
    try:
        subprocess.check_output(cmd)
    except Exception as e:
        msg = "cmdline: %s\nFailed with message \"%s\""%(cmdline, str(e))
        myfunc.WriteFile("[%s] %s\n"%(date_str, msg),  runjob_errfile, "a", True)
        pass

    end_time = time.time()
    runtime_in_sec = end_time - begin_time

    return runtime_in_sec
# }}}
