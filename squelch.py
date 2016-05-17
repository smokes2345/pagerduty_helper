#!/usr/bin/python

import requests,re,datetime
from dateutil import parser
from dateutil.tz import *
from pdlib import PDHelper

if __name__ == "__main__":
	import argparse,sys
	from dateutil import parser

	args = argparse.ArgumentParser()
	args.add_argument('-u','--user-id',type=str,help="Your pagerduty ID")
	args.add_argument('-S','--services',type=str,help="Comma-separated list of services to check",default="PFL7MG7,P7D4556,PQPX4LS,PZP3ZEP,P2B87V2,P54JXV0,PRZWVLI,P1BBCFR,PZR5UCJ,P4NVGV6,PZP3ZEP,PQ3KQT3,PZPNPJM")
	args.add_argument('-D','--domain',type=str,help="Subdomain from PD URL",default='cisco-cis-devops')
	args.add_argument('-k','--key',type=str,help="PD API Key")
	args.add_argument('-U','--snooze-until',type=str,help="Time/Date when alerts should be unack'd (Accumulative)",default='EOS')
	args.add_argument('-d','--days',default=0,type=int,help="Number of days to snooze (Accumulative)")
	args.add_argument('-H','--hours',default=0,type=int,help="Number of hours to snooze (Accumulative)")
	args.add_argument('-m','--minutes',default=30,type=int,help="Number of minutes to snooze (Accumulative)")
	args.add_argument('-s','--seconds',default=0,type=int,help="Number of seconds to snooze (Accumulative)")
	sys.argv.pop(0)
	opts = args.parse_args(sys.argv)
	helper = PDHelper(opts.domain,opts.key,opts.user_id)

	snooze_time = {'days': opts.days,'minutes': opts.minutes,'seconds': opts.seconds}
	if opts.snooze_until == 'EOS':
		print "Using {} for userid".format(opts.user_id)
		snooze_time['until'] = helper.get_eos(opts.user_id)
		print "User {} goes off call at {}".format(opts.user_id,snooze_time['until'])
	elif len(opts.snooze_until) > 3:
		snooze_time['until'] = parser.parse(opts.snooze_until)

	for SERVICE in opts.services.split(','):
			helper.setService(SERVICE)
			payload = {
			    'service':SERVICE,
			    'assigned_to_user': opts.user_id,
			    'sort_by':'created_on:asc',
			    'limit':200,
			}
			resp = requests.get("https://{}.pagerduty.com/api/v1/incidents/".format(opts.domain),headers=helper.headers,params=payload)
			resp.raise_for_status()
			incidents = resp.json()['incidents']
			print "Got {} incidents in service {}".format(len(incidents),SERVICE)	
			for i in incidents:
					url = "https://{}.pagerduty.com/api/v1/incidents/{}/notes".format(opts.domain,i['id'])
					resp = requests.get(url,headers=helper.headers)
					resp.raise_for_status()
					notes = resp.json()['notes']
					for n in notes:
						if re.search('CASE.*CCS[0-9]{9}',n['content']):
							if i['assigned_to_user']['id'] == opts.user_id:
								helper.snooze_incident(i,opts.user_id,**snooze_time)
								pass
	