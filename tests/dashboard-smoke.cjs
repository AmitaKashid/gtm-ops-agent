const vm = require('vm'), fs = require('fs'), assert = require('assert');
const html=fs.readFileSync('docs/index.html','utf8');
const script=html.split('<script>').at(-1).split('</script>')[0];
const els={}; function el(id) {return els[id] ||= {value:'',textContent:'',innerHTML:'',style:{},classList:{add(){},remove(){}},replaceChildren(){}};}
const document={getElementById:el,querySelectorAll:()=>[],addEventListener:(event,fn)=>{if(event==='DOMContentLoaded')fn()},createElement:()=>({})};
const calls=[];let status=200;
const fetch=async (url, options)=>{calls.push(url);return {ok:status===200,status,json:async()=>url.endsWith('/health')?{status:'healthy'}:{company_name:'<script>alert(1)</script>',score:'HIGH',completed:true}}};
const c=vm.createContext({document,window:{GTM_API_URL:'https://example.onrender.com/'},location:{hostname:'amitakashid.github.io',origin:'https://amitakashid.github.io'},fetch,Date,console,alert(){}});
vm.runInContext(script,c);
(async()=>{await c.checkHealth(); assert(calls.includes('https://example.onrender.com/health')); el('lead-company').value='Acme'; await c.analyzeLead(); assert(calls.includes('https://example.onrender.com/leads/analyze')); assert(!el('lead-result').innerHTML.includes('<script>')); assert(el('lead-result').innerHTML.includes('&lt;script&gt;')); status=503; await c.checkHealth();assert.equal(el('apiStatus').textContent,'API unavailable');console.log('Dashboard health, URL normalization, lead request, escaping and failure checks passed');})().catch(e=>{console.error(e);process.exit(1)});
