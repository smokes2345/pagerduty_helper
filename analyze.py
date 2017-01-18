#!/usr/local/bin/python

import requests,re,datetime,json,argparse,sys,threading
from dateutil import parser
from dateutil.tz import *
from pdlib import PDHelper
from tqdm import tqdm

args = argparse.ArgumentParser()
args.add_argument('-u','--user-id',type=str,help="Your pagerduty ID")
#args.add_argument('-S','--services',type=str,help="Comma-separated list of services to check",default="PFL7MG7,P7D4556,PQPX4LS,PZP3ZEP,P2B87V2,P54JXV0,PRZWVLI,P1BBCFR,PZR5UCJ,P4NVGV6,PZP3ZEP,PQ3KQT3,PZPNPJM")
args.add_argument('-D','--domain',type=str,help="Subdomain from PD URL",default='cisco-cis-devops')
args.add_argument('-k','--key',type=str,help="PD API Key",default='64sGKebF8Co9uyNKjJjJ')
sys.argv.pop(0)
opts = args.parse_args(sys.argv)
helper = PDHelper(opts.domain,opts.key,opts.user_id)
incidents = helper.get_incidents()

def count_words(input,accumulator={}):
	content = json.dumps(input)
	for word in re.sub('[^\w]', ' ', content).split():
		try:
			accumulator[word] += 1
		except KeyError:
			accumulator[word] = 1
	return accumulator

def create_threads(func,targets,args,kwargs):
	threads = []
	for t in targets:
		fixed_args = args.insert(0,t)
		thread = threading.Thread(target=func,args=fixed_args,kwargs=kwargs)
		threads.append(thread)
	return threads

def collect_threads(threads):
	while len(threads):
		for t in threads:
			t.join(1)
			if not t.isActive():
				threads.remove(t)

has_case = []
case_threads = create_threads()

no_case_words = {}
has_case_words = {}
threads = []
bar = tqdm(total=len(incidents),desc='Spawning Threads')
for i in incidents:
	if i['id'] in has_case:
		#print "Got case " + case
		t = threading.Thread(target=count_words,args=(i,has_case_words))
	else:
		t = threading.Thread(target=count_words,args=(i,no_case_words))
	t.start()
	threads.append(t)
	bar.update(1)


print "Got {} words with a case".format(len(has_case_words))
print "Got {} words without a case".format(len(no_case_words))
