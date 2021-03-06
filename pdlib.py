import requests,re,datetime
from dateutil import parser
from dateutil.tz import *

def roundTime(dt=None, roundTo=60):
   """Round a datetime object to any time laps in seconds
   dt : datetime.datetime object, default now.
   roundTo : Closest number of seconds to round to, default 1 minute.
   Author: Thierry Husson 2012 - Use it as you want but don't blame me.
   """
   if dt == None : dt = datetime.datetime.now()
   seconds = (dt.replace(tzinfo=None) - dt.min).seconds
   # // is a floor division, not a comment on following line:
   rounding = (seconds+roundTo/2) // roundTo * roundTo
   return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)

class PDHelper:

	def __init__(self,domain,key,user_id=None,service=None):
		self.key = key
		self.domain = domain
		uid = user_id
		if service:
			self.service = service
		self.headers = {
		    'Authorization': 'Token token={0}'.format(self.key),
		    'Content-type': 'application/json',
		}

	def _call_url(self,url,method,headers=None,params=None):
		return getattr(requests,method)(url,headers=headers if headers else self.headers,params=params).json()

	def _query(self,resource=None,url=None,method='get',params={},quiet=False):
		try:
			from tqdm import tqdm
		except ImportError:
			quiet = True
		if not resource and not url:
			raise ValueError(__name__ + " called without a resource or url")
		if resource:
			url = "https://{}.pagerduty.com/api/v1/{}".format(self.domain,resource)
		result = getattr(requests,method)(url,headers=self.headers,params=params).json()
		items = result[resource]
		if 'offset' in result.keys() and result['total'] > result['limit']:
			params['offset'] = result['limit']
			while result['total'] >= params['offset']:
				result = getattr(requests,method)(url,headers=self.headers,params=params).json()
				if not quiet:
					try:
						bar.update(len(result[resource]))
					except NameError:
						bar = tqdm(total=result['total'], desc="Getting {}".format(resource))
						bar.update(result['offset'])
				items += result[resource]
				params['offset'] = result['offset'] + result['limit']
		return items

	def get_incidents(self,payload=None):
		#more = True
		#offset = 0
		#while more:
		#	resp = requests.get("https://{}.pagerduty.com/api/v1/incidents/".format(self.domain),headers=self.headers,params=payload)
		return self._query('incidents','get',params=payload)

	def get_notes(self,incident):
		url = "https://{}.pagerduty.com/api/v1/incidents/{}/notes".format(self.domain,incident)
		resp = requests.get(url,headers=self.headers)
		resp.raise_for_status()
		return resp.json()['notes']

	def setService(self,service_id):
		self.service = service_id

	def ack_incident(self,incident,uid):
		if incident['status'] != "acknowledged":
			url = "https://{}.pagerduty.com/api/v1/incidents/{}/acknowledge".format(self.domain,incident['id'])
			payload = { 'requester_id': uid }
			requests.put(url,headers=self.headers,params=payload).raise_for_status()
			url = "https://{}.pagerduty.com/api/v1/incidents/{}".format(self.domain,incident['id'])
			resp = requests.get(url,headers=self.headers)
			resp.raise_for_status()
			print "Acknowledged {}".format(incident['incident_number'])
			return resp.json()
		else:
			print "{} is already acknoledged".format(incident['incident_number'])
	
	def snooze_incident(self,incident,uid,days=0,hours=0,minutes=0,seconds=0,until=None,rounding=True):
			if incident['status'] not in ['acknowledged']:
				incident = self.ack_incident(incident,uid)
			hours += days * 24
			minutes += hours * 60
			seconds += minutes * 60
			snooze_until = (datetime.datetime.now(tzutc()) if not until else until) + datetime.timedelta(seconds=seconds)
			if rounding:
				precision = seconds
				if minutes > 0:
					precision = minutes * 60
				elif hours > 0:
					precision = hours * 60 * 60
				elif days > 0:
					precision = days * 24 * 60 * 60 
				print "ROUNDING ENABLED: %d" % precision
				snooze_until = roundTime(snooze_until,precision)
			unack_at = datetime.datetime.now(tzutc())
			for act in incident['pending_actions']:
				if act['type'] == "unacknowledge":
					unack_at = parser.parse(act['at'])
			print "{} unacks at {}, trying to snooze until {}".format(incident['incident_number'],unack_at,snooze_until)
			if unack_at < snooze_until:
				duration = snooze_until - datetime.datetime.now(tzutc())
				payload = {
					'duration': int(duration.total_seconds()),
					'requester_id': uid
				}
				url = "https://{}.pagerduty.com/api/v1/incidents/{}/snooze".format(self.domain,incident['id'])
				requests.put(url,headers=self.headers,params=payload).raise_for_status()
				print "Snoozed {} for {} ({})".format(incident['incident_number'],duration,int(duration.total_seconds()))
			else:
				print "Not snoozing {} until {}, already ack'd until {}".format(incident['incident_number'],snooze_until.isoformat(' '),unack_at.isoformat(' '))
	
	def get_case(self,incident):
		url = "https://{}.pagerduty.com/api/v1/incidents/{}/notes".format(self.domain,incident['id'])
		resp = requests.get(url,headers=self.headers)
		resp.raise_for_status()
		notes = resp.json()['notes']
		for n in notes:
			match = re.search('CASE:CCS[0-9]{9}.*',n['content'])
			if match and len(match.group(0)):
				return match.group(0)
		return None

	def get_eos(self,user_id=None):
		import json
		if not user_id:
			user_id = self.uid
		url = "https://{}.pagerduty.com/api/v1/users/{}/on_call".format(self.domain,user_id)
		resp = requests.get(url,headers=self.headers)
		resp.raise_for_status()
		data = resp.json()
		eos = datetime.datetime.now(tzutc())
		for shift in data['user']['on_call']:
			if shift['end'] is not None:
				tmp_eos = parser.parse(shift['end'])
				if tmp_eos > eos:
					eos = tmp_eos
		return eos
