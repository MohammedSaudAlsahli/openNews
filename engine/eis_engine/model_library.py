"""Paged discovery from Ollama's public catalogue, independent of installed models."""
import re
import httpx
from lxml import html
from .contracts import Failure


def document(text):
    return html.fromstring(text, parser=html.HTMLParser(no_network=True))


def parse_search(text):
    doc = document(text)
    rows = []
    for link in doc.xpath('//a[.//h2]'):
        path = link.get('href','')
        if not re.fullmatch(r'/(?:library/)?[\w.-]+(?:/[\w.-]+)?',path): continue
        name = path.removeprefix('/library/').lstrip('/')
        title = ' '.join(link.xpath('.//h2')[0].text_content().split())
        descriptions = link.xpath('.//p')
        labels = [' '.join(x.text_content().split()) for x in link.xpath('.//span')]
        capabilities = [x for x in labels if x in {'embedding','tools','vision','thinking','cloud','decision','audio'}]
        rows.append({'id':name,'name':title,'description':' '.join(descriptions[0].text_content().split()) if descriptions else '',
                     'capabilities':list(dict.fromkeys(capabilities)), 'source':'https://ollama.com'+path})
    more = any('/search?' in x and 'page=' in x for x in doc.xpath('//*[@hx-trigger="revealed"]/@hx-get'))
    return {'models':rows,'has_more':more}


def parse_variants(text, family):
    doc = document(text)
    variants = {}
    prefix = '/library/'+family+':' if '/' not in family else '/'+family+':'
    for link in doc.xpath('//a[@href]'):
        path = link.get('href','')
        if not path.startswith(prefix): continue
        identifier = path.removeprefix('/library/').lstrip('/')
        if not re.fullmatch(r'[\w./-]+:[\w.-]+',identifier): continue
        text = ' '.join(link.text_content().split())
        size = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB|TB)',text)
        value = int(float(size[1])*{'GB':10**9,'MB':10**6,'TB':10**12}[size[2]]) if size else None
        if identifier not in variants or value:
            variants[identifier] = {'id':identifier,'size':value,'cloud':'cloud' in identifier.lower()}
    return {'variants':list(variants.values())}


class ModelLibrary:
    async def search(self, query='', page=1, capability=''):
        if not isinstance(query,str) or len(query)>150 or type(page) is not int or not 1<=page<=10000:
            raise Failure('VALIDATION_ERROR','بحث غير صالح.')
        if capability not in {'','embedding','tools','thinking','vision','decision'}: raise Failure('VALIDATION_ERROR','Invalid capability')
        text = await self.fetch('https://ollama.com/search', {**({'c':capability} if capability else {}),**({'q':query} if query else {}), **({'page':page} if page>1 else {})})
        result = parse_search(text)
        if not result['models'] and ('<html' not in text.lower() and '<li' not in text.lower()):
            raise Failure('CATALOG_UNAVAILABLE','تعذّر تحميل المكتبة. أعد المحاولة.')
        return result

    async def variants(self, family):
        if not isinstance(family,str) or not re.fullmatch(r'[\w.-]+(?:/[\w.-]+)?',family):
            raise Failure('VALIDATION_ERROR','نموذج غير صالح.')
        path = '/library/'+family if '/' not in family else '/'+family
        result = parse_variants(await self.fetch('https://ollama.com'+path+'/tags'),family)
        if not result['variants']: raise Failure('CATALOG_UNAVAILABLE','تعذّر قراءة إصدارات النموذج. أعد المحاولة.')
        return result

    async def fetch(self,url,params=None):
        try:
            async with httpx.AsyncClient(trust_env=False,timeout=7,follow_redirects=True) as client:
                r=await client.get(url,params=params,headers={'HX-Request':'true'} if params and params.get('page',1)>1 else None)
                r.raise_for_status()
                return r.text
        except httpx.HTTPError:
            raise Failure('CATALOG_UNAVAILABLE','تعذّر تحميل المكتبة. تحقق من الإنترنت ثم أعد المحاولة.')
