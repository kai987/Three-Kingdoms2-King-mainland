from pathlib import Path

PROOF = """
const battleProofRoot = new URL('../build/battle-ab-proof/', import.meta.url);
async function battleProof(label, saves) {
 const info = test.info();
 const file = new URL(label + '-' + info.testId + '.json', battleProofRoot);
 const row = {title:info.title, project:info.project.name, label, saves:saves.map(value=>({
  sha256:createHash('sha256').update(JSON.stringify(value)).digest('hex'),
  rng:value.state.rng,
 }))};
 await appendFile(file,JSON.stringify(row)+'\\n');
}
"""

def replace(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)

def prepare(name):
    path = Path('tests', name)
    text = "import {appendFile} from 'node:fs/promises';\nimport {createHash} from 'node:crypto';\n" + path.read_text()
    index = text.index('\n', text.index('import {test,expect}')) + 1
    return path, text[:index] + PROOF + text[index:]

root = Path('build/battle-ab-proof')
root.mkdir(parents=True,exist_ok=True)
path, text = prepare('browser_ui.spec.mjs')
message = "'Playing or skipping a committed soldier round cannot apply its damage or RNG twice'"
old = f' expect(await tacticalSave(page)).toEqual(committed,{message});'
new = f' expect(settled).toEqual(committed,{message});'
if old in text:
    text = replace(text,old,' const checked=await tacticalSave(page);'+old.replace('await tacticalSave(page)','checked')+"\n await battleProof('natural-round',[committed,checked]);")
else:
    text = replace(text,new,new+"\n await battleProof('natural-round',[committed,settled]);")
text = replace(text,'expect(await read()).toEqual(snapshot);', "const reloaded=await read();expect(reloaded).toEqual(snapshot);await battleProof('battle-layout',[pending,committed,snapshot,JSON.parse(raw),reloaded]);")
text = replace(text," const proof=testInfo.outputPath('tactical-identity-and-actions.json');"," await battleProof('battle-movement',[initial.save,moved.save,twice.save,enemyTurn.save,pendingAttack,committed.save,saved.save,JSON.parse(raw),restored.save]);\n const proof=testInfo.outputPath('tactical-identity-and-actions.json');")
path.write_text(text)

path, text = prepare('browser_soldier_ui.spec.mjs')
message = "'Animation completion or Skip cannot resolve another hit or draw extra random numbers'"
old = f' expect(await save(page)).toEqual(committed,{message});'
new = f' expect(settled.save).toEqual(committed,{message});'
if old in text:
    text = replace(text,old,' const checked=await save(page);'+old.replace('await save(page)','checked')+"\n await battleProof('animation',[committed,checked]);")
else:
    text = replace(text,new,new+"\n await battleProof('animation',[committed,settled.save]);")
path.write_text(text)
