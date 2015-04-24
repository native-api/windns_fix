"""Restart the DNS server service
if it has yielded specific errors to the event log.
The script is intended to run as a service shortly after services startup
and stops after doing its job.
"""

errors=404,407,408
service="dns"

# set up logging #####################################
import sys,logging,logging.handlers,os.path
#in this particular case, argv[0] is likely pythonservice.exe deep in python's lib\
# so it makes no sense to write log there
log_file=os.path.splitext(__file__)[0]+".log"
l = logging.getLogger()
l.setLevel(logging.INFO)
f = logging.Formatter('%(asctime)s %(process)d:%(thread)d %(name)s %(levelname)-8s %(message)s')
h=logging.StreamHandler(sys.stdout)
h.setLevel(logging.NOTSET)
h.setFormatter(f)
l.addHandler(h)
h=logging.handlers.RotatingFileHandler(log_file,maxBytes=1024**2,backupCount=1)
h.setLevel(logging.NOTSET)
h.setFormatter(f)
l.addHandler(h)
del h,f
#hook to log unhandled exceptions
def excepthook(type,value,traceback):
    logging.error("Unhandled exception occured",exc_info=(type,value,traceback))
    #Don't need another copy of traceback on stderr
    if old_excepthook!=sys.__excepthook__:
        old_excepthook(type,value,traceback)
old_excepthook = sys.excepthook
sys.excepthook = excepthook
del log_file,os
# ####################################################

class XMLEvent:
    import lxml.etree as etree
    import iso8601
    attr_fns = {
        'EventID':lambda self:int(\
            self.e.xpath('/_:Event/_:System/_:EventID',namespaces=self.nsmap)[0]\
            .text),
        'Time':lambda self:XMLEvent.iso8601.parse_date(\
            self.e.xpath('/_:Event/_:System/_:TimeCreated[@SystemTime]',namespaces=self.nsmap)[0]\
            .attrib['SystemTime'])}
    def __init__(self,xml):
        self.e=XMLEvent.etree.fromstring(xml)
        self.nsmap={'_':self.e.nsmap[None]}   #no default namespace support in lxml as of 04.2015
    def __getattr__(self,attr):
        try: fn=XMLEvent.attr_fns[attr]
        except KeyError: raise AttributeError(attr)
        return fn(self)

def main():
    import win32evtlog
    import win32serviceutil
    # system start event
    hsysq=win32evtlog.EvtQuery("System",win32evtlog.EvtQueryReverseDirection,\
        "*[System[Provider[@Name='eventlog'] and (EventID=6009)]]",None)
    try: he=win32evtlog.EvtNext(hsysq,1)[0]
    except IndexError:
        l.warn("System startup event not found")
        start_time=0
    else:
        start_time=XMLEvent(win32evtlog.EvtRender(he,win32evtlog.EvtRenderEventXml)).Time
        l.info("Last system startup event found at time `%s'"%start_time)
    del hsysq,he
    
    #locate specific errors in DNS log
    evtlog_name="DNS Server"
    service_name=evtlog_name
    
    service_state=win32serviceutil.QueryServiceStatus("dns")[1]
    assert service_state==win32service.SERVICE_RUNNING,\
        "`%s' service is not running when it should; state=%s"%(service,service_state)
    del service_state
    
    hdnsq = win32evtlog.EvtQuery(evtlog_name,win32evtlog.EvtQueryReverseDirection,\
        "*[System["+' or '.join("EventID="+str(code) for code in errors)+"]]",None)
    try: he=win32evtlog.EvtNext(hdnsq,1)[0]
    except IndexError:
        l.info("Specified %s errors are not detected in `%s' log, no action needed"%(service_name,evtlog_name))
        return
    else:
        e = XMLEvent(win32evtlog.EvtRender(he,win32evtlog.EvtRenderEventXml))
        last_error_time=e.Time
        l.info("Found a relevant %s error with code `%d' at time `%s'"%(service_name,e.EventID,last_error_time))
        if last_error_time<start_time:
            l.info("Last error is older that last startup, no action needed")
            return
    del hdnsq,he,evtlog_name
    
    l.info("Restarting `%s' service"%service)
    win32serviceutil.RestartService(service)


import win32serviceutil,win32service
class DnsFixService(win32serviceutil.ServiceFramework):
    _svc_name_="DnsFixService"
    _svc_display_name_="DNS server Win2008 fix"
    _svc_description_="""Workaround for DNS server in Win2008 not starting at system startup with errors 404,407,408 (can't open socket)"""
    _svc_deps_=("tcpip",)
    def SvcDoRun(self):
        #sys.excepthook doesn't seem to work in this routine -
        # apparently, everything is handled by the ServiceFramework machinery
        try:
            l.info("Starting service")
            main()
        except Exception,e:
            excepthook(*sys.exc_info())
        else:
            l.info("Finished successfully")
    def SvcStop(self):
        l.warn("Manual stop request received, ignoring")

if __name__=='__main__':
    win32serviceutil.HandleCommandLine(DnsFixService)
