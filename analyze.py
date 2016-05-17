#!/usr/bin/python

import requests,re,datetime
from dateutil import parser
from dateutil.tz import *
from pdlib import PDHelper
import argparse,sys

args = argparse.ArgumentParser()
args.add_argument('-u','--user-id',nargs=1,help="Your pagerduty ID")
args.add_argument('-S','--services',nargs='?',help="Comma-separated list of services to check",default="PFL7MG7,P7D4556,PQPX4LS,PZP3ZEP,P2B87V2,P54JXV0,PRZWVLI,P1BBCFR,PZR5UCJ,P4NVGV6,PZP3ZEP,PQ3KQT3,PZPNPJM")
args.add_argument('-D','--domain',nargs=1,help="Subdomain from PD URL",default='cisco-cis-devops')
args.add_argument('-k','--key',nargs=1,help="PD API Key",default='64sGKebF8Co9uyNKjJjJ')
#args.add_argument('-U','--snooze-until',nargs=1,help="Time/Date when alerts should be unack'd (Accumulative)",default='EOS')
#args.add_argument('-d','--days',nargs=1,default=0,help="Number of days to snooze (Accumulative)")
#args.add_argument('-H','--hours',nargs=1,default=0,help="Number of hours to snooze (Accumulative)")
#args.add_argument('-m','--minutes',nargs=1,default=30,help="Number of minutes to snooze (Accumulative)")
#args.add_argument('-s','--seconds',nargs=1,default=0,help="Number of seconds to snooze (Accumulative)")
sys.argv.pop(0)
opts = args.parse_args(sys.argv)
helper = PDHelper(opts.domain,opts.key,opts.user_id)
helper.get_incidents()