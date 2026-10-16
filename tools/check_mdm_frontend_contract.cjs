// Executes extracted production transformations without a browser, network,
// React mount, workflow submit, or a parallel hand-written transformation.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert');
const dependencies=process.argv[2], resultPath=process.argv[3], storagePath=process.argv[4], outputPath=process.argv[5];
const ts=require(path.join(dependencies,'typescript')), _=require(path.join(dependencies,'lodash'));
const root=path.resolve(__dirname,'..'), prefix='frontend/src/VectorFlow/Pages/MTA/MDM/';
assert(!fs.existsSync(outputPath));
const sourceHashes={},checks=[];
function read(relative){const text=fs.readFileSync(path.join(root,relative),'utf8');sourceHashes[relative]=crypto.createHash('sha256').update(text).digest('hex');return text;}
function compile(text){return ts.transpileModule(text,{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS}}).outputText;}
function upload(relative){const text=read(prefix+relative); const start=text.indexOf('const postMasterDataChunks = async');assert(start>=0);const body=text.indexOf('=> {',start)+4;const end=text.indexOf('let taskId',body);assert(end>body);return new Function('_',compile('const run=(rowData:any,activeMaster:any)=>{'+text.slice(body,end)+'return rowData;};')+'return run;')(_);}
const transforms={1:upload('AddRecord/useAdd.ts'),2:upload('ViewModify/useViewModify.ts'),3:upload('DeleteRecord/useDelete.ts')};
const helperText=read('frontend/src/helpers/utils.ts'), tree=ts.createSourceFile('utils.ts',helperText,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
function helper(name){let expression;function visit(node){if(ts.isVariableDeclaration(node)&&node.name.getText(tree)===name)expression=node.initializer.getText(tree);ts.forEachChild(node,visit);}visit(tree);assert(expression);return new Function(compile('const fn='+expression+';')+'return fn;')();}
const columns=helper('getExistingColumns'),fields=helper('getExistingColumnFields');
const configs={};for(const filename of fs.readdirSync(path.join(root,'mta/config')).filter(x=>/^mdm_.*\.json$/.test(x))){const p='mta/config/'+filename;for(const row of JSON.parse(read(p)).UI_MDMConfig||[]){(configs[row.MasterId]??=[]).push({key:row.Col_Code,displayName:row.Header,isDownload:row.IsDownload,isDelete:row.IsDelete});}}
const contracts=JSON.parse(fs.readFileSync(resultPath,'utf8').replace(/^\uFEFF/,''));
for(const c of contracts.cases.filter(x=>x.emitted)){
 const actual=transforms[c.action]([c.emitted],{id:c.master,fields:configs[c.master]});assert.deepStrictEqual(actual,[c.wire]);
 checks.push({name:'request '+c.index+' actual frontend wire',status:'PASS',actual});
}
const storage=JSON.parse(fs.readFileSync(storagePath,'utf8').replace(/^\uFEFF/,''));
for(const v of storage.vectors){const row=v.reviewed[0].data[0];const visible=fields(columns(row),configs[12]).map(x=>x.key);assert.equal(visible.includes('ed'),v.label!=='null');checks.push({name:v.label+' reviewer column selection',status:'PASS',visible});}
const nullAdd=transforms[1]([{ed:null,error:'',warning:''}],{id:12,fields:configs[12]});assert.strictEqual(nullAdd[0].ed,null);checks.push({name:'Add transport preserves actual JSON null; workbook emission is earlier boundary',status:'PASS'});
const nullModify=transforms[2]([{nn:null,error:'',warning:''}],{id:13,fields:configs[13]});assert.strictEqual(nullModify[0].nn,'');checks.push({name:'Modify transport converts null to empty string',status:'PASS'});
const report={status:'PASS',checks,sourceHashes,boundary:'Actual extracted TypeScript functions run in Node; not mounted UI/HTTP/permission or workflow evidence'};
fs.writeFileSync(outputPath,JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,checks:checks.length}));
