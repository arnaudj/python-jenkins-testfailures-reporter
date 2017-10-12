#!/usr/bin/env python

# Tested on Jenkins 2.83
# Configure URLs of Jobs to include in the XLS report:
urlblock = """http://jenkins/view/xyz/job/your-project/10042/
http://jenkins/view/xyz/job/your-project/10043/"""


import urllib.request
import json
import pandas as pd
import datetime
    
def skip_proxy():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    urllib.request.install_opener(opener)

def fetch_job_test_data(url):
    payload = download_job_stats("%s%s" % (url, "/testReport/api/json?pretty=true&tree=suites[cases[className,name,status,errorDetails]]"))
    return extract_tests_report(payload)

def download_job_stats(rest_url):
    print("GET %s" % rest_url)
    request = urllib.request.Request(rest_url)
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as e: # http level
        print('HTTPError: %d' % e.code)
        return ""
    except urllib.error.URLError as e: # low level (dns, etc)
        print('URLError: %d' % e.code)
        return ""
    else:
        return response.read().decode('utf-8')

def extract_tests_report(payload):
    print("Processing payload with size %s" % len(payload))
    data = json.loads(payload)
    suites = data["suites"]
    extracted = []
    for suite in suites:
        cases = suite["cases"]
        for item in cases:
            extracted.append({'status': item['status'], 'className': item['className'], 'name': item['name'], 'errorDetails': item['errorDetails']})
    print('Extracted %d tests status lines.' % len(extracted))
    return extracted

def createGroupedDataFrame(job_data):
    df = pd.DataFrame(data=job_data)
    df = df[(df['status'] == 'FAILED') | (df['status'] == 'REGRESSION')]
    df = df[['className', 'errorDetails', 'name']].groupby(['className', 'errorDetails'], as_index=False).count()
    df.rename(columns = {'name':'count'}, inplace = True)
    df = df[['className', 'count', 'errorDetails']]
    df.sort_values('count', ascending=False, inplace=True)
    return df

def get_short_job_name_from_job_url(url):
    d = url.split("/")
    return d[-3]

def main():
    skip_proxy()
    urls = list(urlblock.splitlines())
    urls = list(map(lambda x: x if(x.endswith('/')) else x + '/', urls))
    print('Ready to fetch data for jobs: %s' % urls)

    out_file = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    writer = pd.ExcelWriter(out_file + '.xlsx', engine='xlsxwriter')    

    for url in urls:
        print("Handling job %s" % url)
        job_stats = fetch_job_test_data(url)
        d = createGroupedDataFrame(job_stats)
        d.to_excel(writer, sheet_name=get_short_job_name_from_job_url(url)[-20:])

    writer.save()
    print('Export complete: %d sheet(s).' % len(urls))

main()

#from IPython.display import display, HTML
#display(df)