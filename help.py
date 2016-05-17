#!/usr/bin/python

import requests,re,datetime
from dateutil import parser
from dateutil.tz import *

SUBDOMAIN='cisco-cis-devops'
API_ACCESS_KEY='64sGKebF8Co9uyNKjJjJ'
#API_ACCESS_KEY='SsrMbW9nBSWmWsFp9Zz2'
u_cloud_region=""
INCIDENT_TYPE = ""
ACTIVE = "triggered"
#SERVICES = "PFL7MG7,P7D4556,PQPX4LS,PZP3ZEP,P2B87V2,P54JXV0,PRZWVLI,P1BBCFR,PZR5UCJ,P4NVGV6,PZP3ZEP,PQ3KQT3,PZPNPJM"
#uid = "PSW7J5Z"

#pd = PagerDuty(SUBDOMAIN,API_ACCESS_KEY,page_size=100)

headers = {
    'Authorization': 'Token token={0}'.format(API_ACCESS_KEY),
    'Content-type': 'application/json',
}

def ack_incident(incident,uid):
	if incident['status'] != "acknowledged":
		url = "https://{}.pagerduty.com/api/v1/incidents/{}/acknowledge".format(SUBDOMAIN,incident['id'])
		payload = {
			'requester_id': uid
		}
		requests.put(url,headers=headers,params=payload).raise_for_status()
		url = "https://{}.pagerduty.com/api/v1/incidents/{}".format(SUBDOMAIN,incident['id'])
		resp = requests.get(url,headers=headers)
		resp.raise_for_status()
		print "Acknowledged {}".format(incident['incident_number'])
		return resp.json()
	else:
		print "{} is already acknoledged".format(incident['incident_number'])


def snooze_incident(incident,uid,days=0,hours=0,minutes=0,seconds=0,until=None):
	#try:
		if incident['status'] not in ['acknowledged']:
			incident = ack_incident(incident,uid)
		hours += days * 24
		minutes += hours * 60
		seconds += minutes * 60
		snooze_until = (datetime.datetime.now(tzutc()) if not until else until) + datetime.timedelta(seconds=seconds)
		print "Snoozing until {}".format(snooze_until)
		unack_at = datetime.datetime.now(tzutc())
		for act in incident['pending_actions']:
			if act['type'] == "unacknowledge":
				unack_at = parser.parse(act['at'])

		if unack_at < snooze_until:
			duration = snooze_until - datetime.datetime.now(tzutc())
			payload = {
				'duration': int(duration.total_seconds()),
				'requester_id': uid
			}
			url = "https://{}.pagerduty.com/api/v1/incidents/{}/snooze".format(SUBDOMAIN,incident['id'])
			requests.put(url,headers=headers,params=payload).raise_for_status()
			print "Snoozed {} for {} ({})".format(incident['incident_number'],duration,int(duration.total_seconds()))
		else:
			print "Not snoozing until {}, already ack'd until {}".format(snooze_until.isoformat(' '),unack_at.isoformat(' '))
	#except Exception as e:
	#	print "Could not snooze {}: {}".format(incident['incident_number'],e)

def get_eos(user_id):
	import json
	url = "https://{}.pagerduty.com/api/v1/users/{}/on_call".format(SUBDOMAIN,user_id)
	#payload = {'query': user_id}
	resp = requests.get(url,headers=headers)
	resp.raise_for_status()
	data = resp.json()
	#print "Schedule:\n{}".format(json.dumps(data,indent=3))
	eos = datetime.datetime.now(tzutc())
	for shift in data['user']['on_call']:
		tmp_eos = parser.parse(shift['end'])
		if tmp_eos > eos:
			eos = tmp_eos
	return eos
	#for u in data['users']:
	#	if user_id == u['id']:
	#		print "User:\n{}".format(json.dumps(u),indent=3)
	#		for oncall in u['on_call']:
	#			tmp_eos = parser.parse(oncall['end'])
	#			if tmp_eos > eos:
	#				print "Checking if {} is best".format(tmp_eos)
	#				eos = tmp_eos
	#		return eos

if __name__ == "__main__":
	import argparse,sys
	from dateutil import parser

	args = argparse.ArgumentParser()
	args.add_argument('-U','--snooze-until',nargs=1,help="Time/Date when alerts should be unack'd (Accumulative)",default='EOS')
	#args.add_argument('--snooze-for',nargs='?')
	args.add_argument('-u','--user-id',nargs=1,default='PSW7J5Z',help="Your pagerduty ID")
	args.add_argument('-S','--services',nargs='?',help="Comma-separated list of services to check",default="PFL7MG7,P7D4556,PQPX4LS,PZP3ZEP,P2B87V2,P54JXV0,PRZWVLI,P1BBCFR,PZR5UCJ,P4NVGV6,PZP3ZEP,PQ3KQT3,PZPNPJM")
	args.add_argument('-D','--domain',nargs=1,help="Subdomain from PD URL")
	args.add_argument('-d','--days',nargs=1,default=0,help="Number of days to snooze (Accumulative)")
	args.add_argument('-H','--hours',nargs=1,default=0,help="Number of hours to snooze (Accumulative)")
	args.add_argument('-m','--minutes',nargs=1,default=30,help="Number of minutes to snooze (Accumulative)")
	args.add_argument('-s','--seconds',nargs=1,default=0,help="Number of seconds to snooze (Accumulative)")
	sys.argv.pop(0)
	opts = args.parse_args(sys.argv)

	snooze_time = {'days': opts.days,'minutes': opts.minutes,'seconds': opts.seconds}
	if opts.snooze_until == 'EOS':
		snooze_time['until'] = get_eos(opts.user_id)
		print "User {} goes off call at {}".format(opts.user_id,snooze_time['until'])
	else:
		snooze_time['until'] = parser.parse(opts.snooze_until)

	for SERVICE in opts.services.split(','):
		#try:
			payload = {
			    'service':SERVICE,
			    'assigned_to_user': opts.user_id,
			    'sort_by':'created_on:asc',
			    'limit':200,
			}
			
			resp = requests.get("https://{}.pagerduty.com/api/v1/incidents/".format(SUBDOMAIN),headers=headers,params=payload).json()
			#resp.raise_for_status()
			incidents = resp['incidents']
			print "Got {} incidents in service {}".format(len(incidents),SERVICE)
		
			for i in incidents:
				#try:
					url = "https://{}.pagerduty.com/api/v1/incidents/{}/notes".format(SUBDOMAIN,i['id'])
					notes = requests.get(url,headers=headers).json()['notes']
					#print "Checking for cases in {}".format(i['incident_number'])
					for n in notes:
						if re.search('CASE.*CCS[0-9]{9}',n['content']):
							#print "Found case in {}: {}".format(i['incident_number'],n['content'])
							if i['assigned_to_user']['id'] == opts.user_id:
								print "Snoozing {}".format(i['incident_number'])
								snooze_incident(i,opts.user_id,**snooze_time)
								pass
				#except Exception as e:
				#	print "Skipping {} in service {}: {}".format(i['incident_number'],SERVICE,e)
		#except Exception as e:
		#	print "Skipping service {}: {}".format(SERVICE,e)
	