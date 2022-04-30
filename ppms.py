# -*- coding: utf-8 -*-
# Referring to PPMS.py in the PyGMI
# To work compatibly with PyMeasure.
# The ctypes library includes datatypes for passing data to DLLs.
# For instance, c_int to pass integer pointers.

# Modify the file path in line 108 of ppms.dll to meet the demands.

import ctypes
import os
import re #Regular expression operations
import time
import subprocess
print(__file__)
module_folder = os.path.dirname(__file__)
configmatch = re.compile(r"remote=(?P<rem>True|False);ip=(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3});insttype=(?P<insttype>PPMS|VersaLab|DynaCool|SVSM)")

# Retry decorator with return
def retry_with(tries=2,default_ans=(True,),wait=15):
#    Retries a function until it does not raise an exception or error.
#    It also tries to restart MultiVu if it cannot find it running
#    but it appears the DLL functions already do that by themselves
#    If it runs out of tries, a default answer is returned.
    def deco(f):
        def f_retry(*args, **kwargs):
            mtries = tries # make mutable
            errorstatus = True
            while mtries >0 and errorstatus:
                try:
                    ans = f(*args, **kwargs) # first attempt
                    errorstatus = ans[0]
                except:
                    print('exception in ',f.__name__)
                    errorstatus = True
                if errorstatus:
                    print('Error detected, checking Multivu...')
                    mtries -= 1      # consume an attempt
                    listproc = subprocess.check_output("tasklist")
                    if 'PpmsMvu.exe' not in str(listproc):
                        # not really necessary as it appears the DLL
                        # will do it by itself
                        print('Multivu not running, restarting it now')
                        subprocess.Popen(["C:\\QdPpms\\MultiVu\\PpmsMvu.exe","-macro"])
                    else:
                        print('Multivu already running')
                    print('waiting '+str(wait)+' secs before querying Multivu again')
                    time.sleep(wait)
            if not(errorstatus):
                res = ans
            else:
                print("exception in", f.__name__,"ran out of retries")
                res = default_ans # Ran out of tries :-(
            return res
        return f_retry # true decorator -> decorated function
    return deco


class Connect_Instrument(object):
    def __init__(self, config_line='remote=False;ip=127.0.0.1;insttype=PPMS'):
        match = configmatch.search(config_line)
        if match is None:
            print('address line for QD PPMS or similar must follow this format')
            print('remote=False;ip=127.0.0.1;insttype=PPMS')
            print('please correct and retry instruments initialization')
        else:
            if match.group('rem')=='True':
                remote = True
            else:
                remote = False
            ip_address=match.group('ip')
            insttype=match.group('insttype')

            instdict = {'PPMS':0,
                        'VersaLab':1,
                        'DynaCool':2,
                        'SVSM':3}
            self.t_apprdict = {'FastSettle':0,
                                'NoOvershoot':1}
            self.t_statdict = {0:'TemperatureUnknown',
                                1:'Stable',
                                2:'Tracking',
                                5:'Near',
                                6:'Chasing',
                                7:'Filling',
                                10:'Standby',
                                13:'Disabled',
                                14:'ImpedanceNotFunction',
                                15:'TempFailure'}
            self.h_statdict = {0:'MagnetUnkown',
                                1:'StablePersistent',
                                2:'WarmingSwitch',
                                3:'CoolingSwitch',
                                4:'StableDriven',
                                5:'Iterating',
                                6:'Charging',
                                7:'Discharging',
                                8:'CurrentError',
                                15:'MagnetFailure'}
            self.h_apprdict = {'Linear':0,
                                'NoOvershoot':1,
                                'Oscillate':2}
            self.h_mode = {'Persistent':0,
                            'Driven':1}
            self.a_mode = {'Move to position':0,
                            'Move to limit':1,
                            'Redefine current position':2,
                            "":3}
            self.ppmsdll = ctypes.cdll.LoadLibrary(module_folder+os.sep+r"MyPPMSDLL/MyPPMSDLL.dll")
            #pass pointers using the byref keyword
            # need to specify encoding for python3, str are not simply bytes arrays anymore
            self.ip = ctypes.byref(ctypes.create_string_buffer(ip_address.encode('utf-8'),size=len(ip_address)))
            self.rem = ctypes.c_bool(remote)
            self.insttype = ctypes.c_int32(instdict[insttype])

    def initialize(self):
        """commands executed when the instrument is initialized"""
        pass

    @retry_with(tries=2,default_ans=(True,1e99,'MagnetUnkown'),wait=15)
    def get_field(self):
        #Function Prototype:
#void __cdecl PPMSGetField(char IPAddress[], LVBoolean Remote,
#	int32_t InstrumentType, double *Field, int32_t *FieldStatus,
#	LVBoolean *Errorstatus, int32_t *Errorcode);
        FieldStatus = ctypes.c_int32()
        # in Oe
        Field = ctypes.c_double()
        # error management
        Errorstatus = ctypes.c_bool()
        Errorcode = ctypes.c_int32()
        #Call the Function
        self.ppmsdll.PPMSGetField(self.ip,self.rem,
                                  self.insttype,ctypes.byref(Field),ctypes.byref(FieldStatus),
                                  ctypes.byref(Errorstatus),ctypes.byref(Errorcode))
        return (Errorstatus.value,Field.value,self.h_statdict[FieldStatus.value])

    @retry_with(tries=2,default_ans=(True,1e99,'TemperatureUnknown'),wait=15)
    def get_temperature(self):
        """        
        #Function Prototype:
        #void __cdecl PPMSGetTemp(char IPAddress[], LVBoolean Remote,
        #	int32_t InstrumentType, double *Temperature, int32_t *TemperatureStatus,
        #	LVBoolean *Errorstatus, int32_t *Errorcode);
        """

        TemperatureStatus = ctypes.c_int32()
        # in K
        Temperature = ctypes.c_double()
        # error management
        Errorstatus = ctypes.c_bool()
        Errorcode = ctypes.c_int32()
        #Call the Function
        self.ppmsdll.PPMSGetTemp(self.ip,self.rem,
                                 self.insttype,ctypes.byref(Temperature),ctypes.byref(TemperatureStatus),
                                  ctypes.byref(Errorstatus),ctypes.byref(Errorcode))
        return (Errorstatus.value,Temperature.value,self.t_statdict[TemperatureStatus.value])