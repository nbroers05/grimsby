"use strict";
/* ============ DATA: regio's en verbindingen ============ */
const REG = [
 {id:"dlpfc",k:"dlPFC",n:"Dorsolaterale prefrontale cortex",kj:"前頭前野",p:[-1.15,0.55,0.45],rol:"Working memory and planning",doet:"Holds a few things at once and keeps him on his plan. Calms the amygdala down when nothing is really wrong.",knop:"Plan discipline and impulse control."},
 {id:"ofc",k:"OFC",n:"Orbitofrontal cortex",kj:"眼窩前頭",p:[-1.35,-0.25,0.3],rol:"Value of options",doet:"Gives every action at every place an expected value, and updates it from dopamine prediction errors.",knop:"Spatial memory sets the learning rate here."},
 {id:"acc",k:"ACC",n:"Anterieure cingulate cortex",kj:"帯状回",p:[-0.55,0.45,0.05],rol:"Doubt and errors",doet:"Fires when two options are almost equally good. He hesitates for a moment and becomes more alert.",knop:"Sensitivity to doubt."},
 {id:"bg",k:"striatum",n:"Basal ganglia (striatum)",kj:"線条体",p:[-0.2,0.05,0.42],rol:"Action selection and habits",doet:"Lets one action win. What he often does at the same place becomes a habit that counts regardless of what it gets him.",knop:"Habit."},
 {id:"motor",k:"motor",n:"Motor cortex",kj:"運動野",p:[-0.15,1.0,0.35],rol:"Movement",doet:"Drives wings and legs as soon as the basal ganglia let an action through.",knop:"None."},
 {id:"cer",k:"cerebellum",n:"Cerebellum",kj:"小脳",p:[1.15,-0.8,0.3],rol:"Timing and skill",doet:"Fine-tunes flying and drawing. The more he does something, the less often it fails.",knop:"Learning speed."},
 {id:"thal",k:"thalamus",n:"Thalamus",kj:"視床",p:[0.15,0.05,0.12],rol:"Gatekeeper",doet:"Everything that comes in passes through here. During sleep the gate mostly closes.",knop:"How lightly he sleeps."},
 {id:"vis",k:"visual",n:"Visual cortex",kj:"視覚野",p:[1.5,0.15,0.35],rol:"Seeing",doet:"Recognises what lies around him. For a crow, shiny things count extra.",knop:"Curiosity."},
 {id:"hip",k:"hippocampus",n:"Hippocampus",kj:"海馬",p:[0.45,-0.3,0.62],rol:"Memories and map",doet:"Remembers what, where and when. Replays the day at night, which strengthens what he learned.",knop:"Spatial memory."},
 {id:"amy",k:"amygdala",n:"Amygdala",kj:"扁桃体",p:[-0.15,-0.48,0.68],rol:"Fright and emotional weight",doet:"Learns in one go that a place is scary. That slowly fades if nothing else happens there.",knop:"Jumpiness and grudges."},
 {id:"hyp",k:"hypothalamus",n:"Hypothalamus",kj:"視床下部",p:[-0.25,-0.5,0.08],rol:"Hunger and rest",doet:"Keeps the body in balance and switches on the needs that get him moving.",knop:"How fast needs build up."},
 {id:"scn",k:"clock",n:"Suprachiasmatic nucleus",kj:"体内時計",p:[-0.42,-0.62,0.0],rol:"Day and night rhythm",doet:"The internal clock. Together with sleep pressure it decides when he goes to sleep.",knop:"Chronotype."},
 {id:"vta",k:"dopamine",n:"VTA (dopamine)",kj:"ドーパミン",p:[0.2,-0.58,0.05],rol:"Prediction error",doet:"Fires when something turns out better than expected and dips when it disappoints. The OFC learns from that.",knop:"Optimism."},
 {id:"lc",k:"noradrenaline",n:"Locus coeruleus",kj:"青斑核",p:[0.62,-0.82,0.12],rol:"Alertness and exploring",doet:"Surprise and threat raise alertness, and with it the urge to try something new.",knop:"Urge to explore."},
 {id:"raphe",k:"serotonin",n:"Raphe nuclei",kj:"セロトニン",p:[0.45,-0.75,-0.12],rol:"Patience and mood",doet:"Decides how much a reward far away is still worth, and colours his mood.",knop:"Patience."},
 {id:"ins",k:"insula",n:"Insula",kj:"島皮質",p:[-0.35,0.0,0.88],rol:"Body sense and disgust",doet:"Feels hunger and tiredness. One bad meal gives an aversion that hardly ever goes away.",knop:"Sensitive stomach."},
 {id:"dmn",k:"default mode",n:"Default mode network",kj:"デフォルト",p:[0.55,0.82,0.05],rol:"Daydreaming",doet:"Active when he has nothing to do. Brings up memories and makes up wishes. Switches off when he concentrates.",knop:"Tendency to daydream."},
 {id:"tpj",k:"theory of mind",n:"Temporoparietal junction",kj:"心の理論",p:[0.85,0.5,0.75],rol:"Understanding others",doet:"Keeps track of whether each visitor can be trusted. Crows remember faces for years.",knop:"Grudges."},
 {id:"taal",k:"language",n:"Language areas",kj:"言語野",p:[-0.65,0.12,0.9],rol:"Reading and talking",doet:"Reads notes and puts thoughts into words. Later the language model does this part, the rest stays code.",knop:"Voice."}
];
const RI = {}; REG.forEach((r,i)=>RI[r.id]=i);
const EDGES = [
 ["thal","vis",.6],["vis","thal",.25],["thal","amy",.5],["vis","amy",.35],["vis","hip",.35],["vis","tpj",.3],
 ["thal","dlpfc",.35],["hip","dlpfc",.35],["dlpfc","hip",.25],["amy","hyp",.45],["amy","lc",.55],["amy","bg",.3],
 ["hyp","vta",.35],["hyp","bg",.45],["hyp","ins",.4],["ins","acc",.35],["ins","amy",.3],["ofc","bg",.55],
 ["ofc","vta",.3],["vta","bg",.6],["vta","ofc",.45],["vta","dlpfc",.25],["vta","hip",.3],["lc","thal",.35],
 ["lc","dlpfc",.3],["lc","vis",.3],["raphe","ofc",.3],["raphe","amy",-.4],["dlpfc","bg",.4],["dlpfc","amy",-.4],
 ["acc","dlpfc",.45],["acc","lc",.3],["bg","motor",.55],["bg","thal",-.3],["motor","cer",.55],["cer","motor",.3],
 ["cer","thal",.25],["scn","hyp",.45],["hip","dmn",.45],["dmn","hip",.3],["dmn","dlpfc",-.3],["dlpfc","dmn",-.3],
 ["tpj","dmn",.3],["tpj","ofc",.3],["taal","tpj",.3],["vis","taal",.3],["dlpfc","taal",.3],["hip","amy",.25],["hip","ofc",.3]
].map(([a,b,w])=>({a:RI[a],b:RI[b],w}));

/* ============ WERELD ============ */
const PLACES = {
 speeltuin:"the playground by his nest", ah:"the AH", jumbo:"the Jumbo", turk:"De Turk", mcd:"the McDonald's",
 centrum:"Cafe Het Centrum", metro:"Rodenrijs station", baken:"Het Baken", voetbal:"the football field", windas:"De Windas"
};
const QUALITY = {ah:.72, jumbo:.52, turk:.82, mcd:.62};
const ACTIONS = {
 eten:{label:"eating", places:["ah","jumbo","turk","mcd"], fx:{honger:-.55}, dur:15},
 slapen:{label:"sleeping", places:["speeltuin"], fx:{rust:-.8}, dur:90},
 tekenen:{label:"drawing", places:["baken"], fx:{expressie:-.6}, dur:25},
 briefjes:{label:"reading notes", places:["windas"], fx:{nieuwsgierig:-.35, sociaal:-.2}, dur:15},
 mensen:{label:"watching people", places:["metro","centrum"], fx:{sociaal:-.5}, dur:20},
 verkennen:{label:"poking around", places:["voetbal","metro","windas","speeltuin"], fx:{nieuwsgierig:-.5}, dur:20},
 internet:{label:"on the internet", places:["centrum"], fx:{nieuwsgierig:-.35, expressie:-.15}, dur:25},
 zitten:{label:"sitting still", places:["*"], fx:{stilte:-.55, rust:-.12}, dur:15}
};
const NEEDS = ["honger","rust","nieuwsgierig","sociaal","expressie","stilte"];
const NEEDLABEL = {honger:"hunger",rust:"rest",nieuwsgierig:"curiosity",sociaal:"social",expressie:"expression",stilte:"quiet"};

/* ============ KARAKTER ============ */
const KNOBS = [
 ["nieuwsgierig","Curiosity"],["schrik","Jumpiness"],["neofobie","Neophobia"],["gewoonte","Habit"],
 ["geduld","Patience"],["verkennen","Exploring"],["geheugen","Spatial memory"],["wrok","Grudges"],["nacht","Night animal"]
];
const PRESETS = {
 crow:{nieuwsgierig:.85,schrik:.55,neofobie:.75,gewoonte:.4,geduld:.3,verkennen:.7,geheugen:.9,wrok:.9,nacht:.15},
 human:{nieuwsgierig:.6,schrik:.4,neofobie:.3,gewoonte:.65,geduld:.7,verkennen:.4,geheugen:.5,wrok:.3,nacht:.4},
 pigeon:{nieuwsgierig:.2,schrik:.5,neofobie:.5,gewoonte:.95,geduld:.2,verkennen:.15,geheugen:.4,wrok:.2,nacht:.1}
};

/* ============ STAAT ============ */
const clamp = (x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const rnd = (a,b)=>a+Math.random()*(b-a);
const pick = arr=>arr[Math.floor(Math.random()*arr.length)];
function freshState(){
  return {
    v:1, t:8*60, place:"speeltuin", act:null, actLeft:0, travelTo:null, preset:"crow", P:{...PRESETS.crow},
    needs:{honger:.4,rust:.2,nieuwsgierig:.5,sociaal:.3,expressie:.3,stilte:.2},
    energie:.85, mood:.1, V:{}, N:{}, habit:{}, fear:{}, aversion:{}, skill:{tekenen:.2,vliegen:.5},
    rpeAvg:0, asleep:false, thought:"Awake. Playground. Everything still where it was.", wish:[],
    counts:{acties:0,prikkels:0}, started:Date.now()
  };
}
let S = freshState();
let EVENTS = [];           // alles sinds deze pagina openstaat
let PENDING = [];          // nog niet naar db
const A = new Float32Array(REG.length);   // activatie
const D = new Float32Array(REG.length);   // drive van buiten
const SP = new Float32Array(REG.length);  // korte pieken
function spike(id,v){ SP[RI[id]] = clamp(SP[RI[id]]+v,0,1.4); }

/* ============ HET BREIN: een tick = 1 gesimuleerde minuut ============ */
function minuteOfDay(){ return S.t % 1440; }
function isNight(){
  const shift = (S.P.nacht-.2)*360; // nachtdier slaapt later
  const m = (minuteOfDay() - shift + 1440) % 1440;
  return m < 6*60 || m >= 22*60;
}
function key(a,p){ return a+"@"+p; }

function tick(){
  S.t += 1;
  const P = S.P, night = isNight();
  // behoeftes lopen op
  const nd = S.needs;
  if (!S.asleep){
    nd.honger += .0022;
    nd.rust += night ? .0045 : .0012;
    nd.nieuwsgierig += .0012 + .0018*P.nieuwsgierig;
    nd.sociaal += .0013;
    nd.expressie += .0009;
    nd.stilte += .0010;
    S.energie = clamp(S.energie - .0008 - (S.act && S.act!=="zitten" ? .0006 : 0));
  } else {
    nd.honger += .0008;
    S.energie = clamp(S.energie + .004);
  }
  NEEDS.forEach(n=>nd[n]=clamp(nd[n]));
  // angst dooft uit als er niks gebeurt (traag bij veel wrok)
  for (const p in S.fear){ S.fear[p] *= (1 - .0015*(1.1-P.wrok)); if (S.fear[p]<.01) delete S.fear[p]; }
  // lopende actie
  if (S.travelTo){
    S.actLeft--;
    if (S.actLeft<=0){ S.place = S.travelTo; S.travelTo=null; arrive(); }
  } else if (S.act){
    S.actLeft--;
    const fx = ACTIONS[S.act].fx, dur = S.actDur || ACTIONS[S.act].dur;
    for (const n in fx) nd[n] = clamp(nd[n] + fx[n]/dur);
    if (S.actLeft<=0) finish();
    else if (S.asleep && !isNight() && nd.rust<.25 && Math.random()<.05) finish();
  } else {
    choose();
  }
  // slaapdruk wint altijd 's nachts
  S.rpeAvg *= .995;
  brain(night);
}

function arrive(){
  spike("hip",.5); spike("vis",.4); spike("thal",.3);
  const f = S.fear[S.place]||0;
  if (f>.3){ spike("amy",f*.8); spike("lc",f*.5); say(`Back at ${PLACES[S.place]}. Something happened here. Staying alert.`); }
  if (S.pendingAct){ start(S.pendingAct.a, S.pendingAct.dur); S.pendingAct=null; }
}

function utility(a,p){
  const P=S.P, nd=S.needs, def=ACTIONS[a];
  let u=0;
  for (const n in def.fx) u += nd[n] * (-def.fx[n]) * 2.2 * (n==="honger"&&nd.honger>.7?1.6:1);
  if (a==="slapen"){ u *= isNight()?2.2:.5; if (isNight()) u += .5; }
  if (a!=="slapen" && isNight()) u -= .25;
  const k=key(a,p);
  u += (S.V[k]||0)*.6;
  u += (S.habit[k]||0)*P.gewoonte*.6;
  u -= (S.fear[p]||0)*(.6+P.schrik);
  u -= (S.aversion[p]||0)*1.6;
  if (p!==S.place) u -= .12*(1-P.geduld) + .04;
  const na = A[RI.lc];
  u += (Math.random()-.5)*(.12 + P.verkennen*.3 + na*.35);
  return u;
}

function choose(){
  const opts=[];
  for (const a in ACTIONS){
    const places = ACTIONS[a].places[0]==="*" ? [S.place] : ACTIONS[a].places;
    for (const p of places) opts.push({a,p,u:utility(a,p)});
  }
  opts.sort((x,y)=>y.u-x.u);
  const best=opts[0], second=opts[1];
  spike("bg",.6); spike("ofc",.45); spike("dlpfc",.25);
  if (second && best.u-second.u < .04){
    spike("acc",.7); spike("lc",.2);
    log("twijfel", `Hesitates between ${ACTIONS[best.a].label} at ${PLACES[best.p]} and ${ACTIONS[second.a].label} at ${PLACES[second.p]}.`);
  }
  const dur = best.a==="slapen" ? (isNight()? 120 : 35) : ACTIONS[best.a].dur;
  if (best.p !== S.place){
    S.travelTo = best.p; S.actLeft = 4 + Math.round(rnd(0,4)); S.act=null;
    S.pendingAct = {a:best.a, dur};
    spike("motor",.6); spike("cer",.6);
    S.thought = thoughtTravel(best.a,best.p);
    log("actie", `Flies to ${PLACES[best.p]} for some ${ACTIONS[best.a].label}.`);
  } else start(best.a, dur);
  S.counts.acties++;
}

function start(a,dur){
  S.act=a; S.actLeft=dur; S.actDur=dur; S.asleep = (a==="slapen");
  const k=key(a,S.place);
  S.habit[k] = clamp((S.habit[k]||0) + .03);
  S.thought = thoughtStart(a);
  if (a==="slapen") log("actie","Goes to sleep in the nest.");
  else log("actie", `Starts ${ACTIONS[a].label} at ${PLACES[S.place]}.`);
}

function finish(){
  const a=S.act, p=S.place, k=key(a,p), P=S.P;
  let r;
  if (a==="eten"){
    r = (QUALITY[p]||.5) + rnd(-.25,.25);
    if (p==="turk" && Math.random()<.05) { badFood(p); r=-1; }
  } else if (a==="slapen"){ r = .5 + rnd(-.1,.1); }
  else if (a==="tekenen"){
    const ok = Math.random() < .35 + S.skill.tekenen*.6;
    S.skill.tekenen = clamp(S.skill.tekenen + .02);
    spike("cer",.5);
    r = ok ? .6 : -.1;
    if (!ok) S.thought = "Drew a tree. It became a pole. I am calling it abstract.";
  } else r = .35 + rnd(-.3,.3) - (S.fear[p]||0)*.5;
  const rpe = r - (S.V[k]||0);
  const alpha = .08 + .25*P.geheugen;
  S.V[k] = (S.V[k]||0) + alpha*rpe;
  S.N[k] = (S.N[k]||0) + 1;
  S.rpeAvg = S.rpeAvg*.8 + rpe*.2;
  S.mood = clamp(S.mood*.9 + r*.1, -1, 1);
  if (rpe>0) spike("vta", clamp(rpe*1.4)); else spike("lc", clamp(-rpe*.8));
  if (Math.abs(rpe)>.3) log("leer", `${rpe>0?"Better":"Worse"} than expected: ${ACTIONS[a].label} at ${PLACES[p]} (prediction error ${rpe>0?"+":""}${rpe.toFixed(2)}).`, {rpe});
  if (a==="slapen"){ S.asleep=false; log("actie","Wakes up."); S.thought = pick(["Awake. I dreamt about bread. Or it was real.","Morning. The playground is still there.","Awake. My feathers are doing something weird."]); }
  else if (a!=="tekenen" || !S.thought.startsWith("Drew a tree")) S.thought = thoughtEnd(a,p,rpe);
  S.act=null; S.actLeft=0;
}

function badFood(p){
  const P=S.P;
  S.aversion[p] = clamp((S.aversion[p]||0) + .7 + .3*P.wrok);
  spike("ins",1); spike("amy",.5); spike("hyp",.4);
  S.thought = `Something from ${PLACES[p]} went down very wrong. Never going there again. Never.`;
  log("leer", `Bad food at ${PLACES[p]}. Aversion learned in one go (Garcia effect).`);
}

function brain(night){
  const P=S.P, nd=S.needs, a=S.act;
  const awake = !S.asleep;
  D.fill(0);
  const set=(id,v)=>D[RI[id]]=Math.max(D[RI[id]],v);
  set("hyp", Math.max(nd.honger, nd.rust)*.8);
  set("scn", night?.55:.2);
  set("ins", nd.honger*.4 + (1-S.energie)*.4);
  set("amy", (S.fear[S.place]||0)*.7);
  set("raphe", (S.mood+1)/2*.5);
  set("vta", .15 + Math.max(0,S.rpeAvg)*.5);
  set("lc", .1 + Math.abs(S.rpeAvg)*.6);
  if (awake){
    set("thal",.25); set("vis",.25); set("dlpfc",.25);
    if (S.travelTo){ set("motor",.65); set("cer",.65); }
    if (a==="tekenen"){ set("motor",.5); set("cer",.7); set("dlpfc",.45); }
    if (a==="eten"){ set("ins",.6); set("hyp",.5); }
    if (a==="briefjes"){ set("taal",.7); set("vis",.5); set("tpj",.4); }
    if (a==="mensen"){ set("tpj",.7); set("vis",.45); }
    if (a==="internet"){ set("taal",.55); set("vis",.55); set("dlpfc",.45); }
    if (a==="verkennen"){ set("hip",.5); set("vis",.5); set("motor",.35); }
    if (a==="zitten"){ set("dmn",.75); set("hip",.35); }
    if (!a && !S.travelTo){ set("dmn",.4); }
  } else {
    set("dmn",.25);
    if (Math.random()<.08){ spike("hip",.7); spike("vta",.15); } // replay
  }
  // dynamiek: 3 substappen
  for (let s=0;s<3;s++){
    const inp = new Float32Array(REG.length);
    for (const e of EDGES) inp[e.b] += e.w * A[e.a] * .38;
    const gate = awake ? 1 : .45;
    for (let i=0;i<REG.length;i++){
      let x = D[i] + SP[i] + inp[i];
      if (!awake && REG[i].id!=="hip" && REG[i].id!=="scn" && REG[i].id!=="hyp") x *= gate;
      const target = clamp(x);
      A[i] += (target - A[i]) * .3;
    }
  }
  for (let i=0;i<SP.length;i++) SP[i]*=.82;
}

/* ============ PRIKKELS ============ */
const STIM = {
 eten:{t:"Give food",d:"someone throws him a chip",run(){
   spike("vis",.7); spike("thal",.6); spike("hyp",.4);
   const surprise = .6;
   spike("vta", surprise); spike("ofc",.4);
   S.needs.honger = clamp(S.needs.honger-.3); S.mood=clamp(S.mood+.15,-1,1);
   const k=key("eten",S.place); S.V[k]=(S.V[k]||0)+.15*(.08+.25*S.P.geheugen)*4;
   S.thought="A chip. Out of nowhere. I do not trust it. I am eating it anyway.";
   return `Someone gives him food at ${PLACES[S.place]}. Positive prediction error, the place is worth more now.`; }},
 schrik:{t:"Whistle / scare",d:"a loud bang or a whistle",run(){
   const P=S.P;
   spike("thal",1); spike("amy",.8+P.schrik*.6); spike("lc",.9); spike("hyp",.3); spike("motor",.5);
   S.fear[S.place] = clamp((S.fear[S.place]||0) + .35 + .5*P.schrik);
   S.mood = clamp(S.mood-.2,-1,1);
   if (S.asleep){ S.asleep=false; }
   const away = Object.keys(PLACES).filter(p=>p!==S.place);
   S.act=null; S.pendingAct=null; S.travelTo = pick(away); S.actLeft=3;
   S.thought="Bang. Out of here. I will remember this place.";
   return `Gets a fright at ${PLACES[S.place]} and flees to ${PLACES[S.travelTo]}. Fear now tied to that place.`; }},
 briefje:{t:"Note",d:"a visitor leaves a note",run(){
   spike("vis",.5); spike("taal",.8); spike("tpj",.5); spike("hip",.3);
   S.needs.nieuwsgierig=clamp(S.needs.nieuwsgierig-.15); S.needs.sociaal=clamp(S.needs.sociaal-.15);
   S.thought=pick(["A note. Something in human language. I read it twice.","Someone thought of me. Suspicious, but nice."]);
   return `Gets a note at ${PLACES[S.place]}.`; }},
 bezoeker:{t:"Visitor",d:"someone comes and stands close",run(){
   const P=S.P;
   spike("vis",.6); spike("tpj",.8); spike("amy",.3*P.neofobie+.1); spike("lc",.3);
   S.needs.sociaal=clamp(S.needs.sociaal-.2);
   S.thought = P.neofobie>.6 ? "A human. I keep two metres away and watch what he does." : "A human. Maybe he has bread.";
   return `A visitor comes by at ${PLACES[S.place]}.`; }},
 glim:{t:"Shiny thing",d:"something sparkles on the ground",run(){
   const P=S.P;
   spike("vis",1); spike("vta",.5+P.nieuwsgierig*.4); spike("hip",.5); spike("amy",.2*P.neofobie); spike("dlpfc",.4);
   S.needs.nieuwsgierig=clamp(S.needs.nieuwsgierig-.3);
   S.wish.unshift("something shiny from "+PLACES[S.place]); S.wish=S.wish.slice(0,5);
   S.thought="It shines. I am taking it. It is mine now, those are the rules.";
   return `Finds something shiny at ${PLACES[S.place]}. Curiosity and dopamine go up.`; }},
 onweer:{t:"Thunderstorm",d:"thunder and rain",run(){
   spike("thal",.8); spike("amy",.5); spike("lc",.8); spike("hyp",.5); spike("scn",.3);
   S.needs.rust=clamp(S.needs.rust+.25); S.mood=clamp(S.mood-.1,-1,1);
   if (S.place!=="speeltuin"){ S.act=null; S.travelTo="speeltuin"; S.actLeft=5; S.pendingAct={a:"zitten",dur:30}; }
   S.thought="Thunder. To the nest. I am not scared, I am sensible.";
   return "Thunderstorm. He takes shelter at his nest."; }},
 bedorven:{t:"Bad food",d:"the food goes down wrong",run(){
   const p = QUALITY[S.place]!==undefined ? S.place : "turk";
   badFood(p); return `Bad food, tied to ${PLACES[p]}.`; }}
};
function stimulus(kind, extra){
  const msg = STIM[kind].run();
  S.counts.prikkels++;
  log("prikkel", (extra?`"${extra}" → `:"") + msg, {stim:kind});
}
function parseText(txt){
  const t = txt.toLowerCase();
  if (/(rotten|spoiled|sick|mouldy|moldy|gross)/.test(t)) return "bedorven";
  if (/(fries|chip|bread|food|feed|cheese|snack|crumb|seed|nut)/.test(t)) return "eten";
  if (/(bang|boo|scare|whistle|stone|rock|shout|scream|bark|firework)/.test(t)) return "schrik";
  if (/(thunder|rain|storm|lightning)/.test(t)) return "onweer";
  if (/(shin|coin|key|silver|gold|ring|bottle cap|sparkl|glitter)/.test(t)) return "glim";
  if (/(note|letter|writes|says|message)/.test(t)) return "briefje";
  return "bezoeker";
}

/* ============ GEDACHTES (code, nog geen taalmodel) ============ */
function thoughtTravel(a,p){
  if (a==="eten") return `Hungry. Off to ${PLACES[p]}. ${S.V[key("eten",p)]>.5?"It was good there.":"Let us see."}`;
  if (a==="slapen") return "Getting dark. Home.";
  return `Going to ${PLACES[p]}. No reason. Just a feeling.`;
}
function thoughtStart(a){
  const T = {
    eten:["Food. Finally.","Eating now. Do not disturb."],
    slapen:["Eyes shut. Tomorrow again.","The nest is cold. Fine."],
    tekenen:["Going to draw something. It will probably be a pole.","Art. Nobody asked for it."],
    briefjes:["Checking for post.","Notes in the sand. My kind of internet."],
    mensen:["Watching people. They do such odd things with their hands.","I sit here and judge."],
    verkennen:["Poking around. There is always something.","I am looking for nothing. That is the fun part."],
    internet:["Online. Checking what Pino is up to.","Cafe wifi. Nobody knows I am here."],
    zitten:["Sitting. Thinking about nothing. Half working.","Quiet for a bit. My head is loud enough."]
  };
  return pick(T[a]);
}
function thoughtEnd(a,p,rpe){
  if (rpe>.3) return `${PLACES[p][0].toUpperCase()+PLACES[p].slice(1)} was better than I thought. Noted.`;
  if (rpe<-.3) return `${PLACES[p][0].toUpperCase()+PLACES[p].slice(1)} was a letdown. One more chance. Maybe.`;
  return pick(["Done. Now what.","That was that.","Fine. Nothing special."]);
}
function say(t){ S.thought=t; }

/* ============ LOG ============ */
function snap(){ const o={}; REG.forEach((r,i)=>o[r.id]=+A[i].toFixed(2)); return o; }
function log(kind, text, extra){
  const ev = {t:S.t, kind, text, place:S.place, needs:Object.fromEntries(NEEDS.map(n=>[n,+S.needs[n].toFixed(2)])), brain:snap(), ...(extra||{})};
  EVENTS.push(ev); if (EVENTS.length>3000) EVENTS.shift();
  PENDING.push(ev);
  addFeed(ev);
}

/* ============ UI ============ */
const $ = id=>document.getElementById(id);
function fmtTime(t){ const d=Math.floor(t/1440)+1, m=t%1440; return `day ${d} · ${String(Math.floor(m/60)).padStart(2,"0")}:${String(m%60).padStart(2,"0")}`; }
function fmtShort(t){ const m=t%1440; return `${String(Math.floor(m/60)).padStart(2,"0")}:${String(m%60).padStart(2,"0")}`; }
function addFeed(ev){
  const f=$("feed"); const d=document.createElement("div");
  d.className="ev "+ev.kind;
  const tm=document.createElement("span"); tm.className="tm"; tm.textContent=fmtShort(ev.t);
  const tx=document.createElement("span"); tx.textContent=ev.text;
  d.append(tm,tx); f.prepend(d);
  while (f.children.length>80) f.lastChild.remove();
}
let selected = RI.amy;
function renderDetail(){
  const r=REG[selected];
  $("dFile").textContent = r.id+".txt"; $("dKanji").textContent = r.kj;
  const inc = EDGES.filter(e=>e.b===selected), out = EDGES.filter(e=>e.a===selected);
  const btn = (e,other)=>`<button data-r="${other}" class="${e.w<0?"inh":""}">${e.w<0?"inhibits ":""}${REG[other].k} <span class="muted">${Math.abs(e.w).toFixed(2)}</span></button>`;
  $("detail").innerHTML = `
    <h2>${r.n}</h2>
    <div class="meterrow" style="margin-top:8px"><span class="px">activation</span><span class="m"><span id="dMeter"></span></span><span class="v" id="dVal">0</span></div>
    <dl>
      <div><dt>role</dt><dd>${r.rol}</dd></div>
      <div><dt>what it does in grimsby</dt><dd>${r.doet}</dd></div>
      <div><dt>knob per character</dt><dd>${r.knop}</dd></div>
      <div><dt>gets input from</dt><dd><div class="conns">${inc.map(e=>btn(e,e.a)).join("")||"<span class='muted'>nothing</span>"}</div></dd></div>
      <div><dt>sends to</dt><dd><div class="conns">${out.map(e=>btn(e,e.b)).join("")||"<span class='muted'>nothing</span>"}</div></dd></div>
    </dl>`;
  $("detail").querySelectorAll("button[data-r]").forEach(b=>b.addEventListener("click",()=>select(+b.dataset.r)));
}
function select(i){ selected=i; renderDetail(); }

function renderNeeds(){
  $("needs").innerHTML = NEEDS.map(n=>`<div class="meterrow"><span>${NEEDLABEL[n]}</span><span class="m"><span style="width:${Math.round(S.needs[n]*100)}%;${S.needs[n]>.75?"background:var(--red)":""}"></span></span><span class="v">${Math.round(S.needs[n]*100)}</span></div>`).join("");
  const rows = Object.keys(S.V).map(k=>({k,v:S.V[k],n:S.N[k]||0})).sort((a,b)=>b.v-a.v).slice(0,8);
  $("beliefs").innerHTML = rows.length ? rows.map(r=>{const [a,p]=r.k.split("@"); return `<tr><td>${ACTIONS[a].label} @ ${PLACES[p]}</td><td style="color:${r.v<0?"var(--red)":"inherit"}">${r.v.toFixed(2)}</td><td>${r.n}</td></tr>`;}).join("") : `<tr><td colspan="3" class="muted">Nothing learned yet. He just woke up.</td></tr>`;
  const fears = Object.entries(S.fear).filter(([,v])=>v>.05).map(([p,v])=>`${PLACES[p]} (${v.toFixed(2)})`);
  const avs = Object.entries(S.aversion).map(([p,v])=>`${PLACES[p]} (${v.toFixed(2)})`);
  $("fearLine").textContent = `Afraid of: ${fears.join(", ")||"nothing"}. Averse to: ${avs.join(", ")||"nothing"}.`;
}
function renderNow(){
  $("clock").textContent = fmtTime(S.t);
  const where = S.travelTo ? `on his way to ${PLACES[S.travelTo]}` : PLACES[S.place];
  $("sPlace").textContent = where;
  $("sThought").textContent = `"${S.thought}"`;
  $("sAct").textContent = S.travelTo ? "flying" : (S.act ? ACTIONS[S.act].label : "choosing");
  $("sMood").textContent = S.mood>.25?"good":S.mood>-.1?"fine":S.mood>-.4?"grumpy":"bad";
  $("sEnergy").textContent = Math.round(S.energie*100)+"%";
  $("hudNow").textContent = `${S.asleep?"asleep":S.travelTo?"flying":S.act?ACTIONS[S.act].label:"choosing"} · ${S.travelTo?PLACES[S.travelTo]:PLACES[S.place]}`;
  const order = [...REG.keys()].sort((a,b)=>A[b]-A[a]).slice(0,5);
  $("topList").innerHTML = order.map(i=>`<div class="meterrow"><span>${REG[i].k}</span><span class="m"><span style="width:${Math.round(A[i]*100)}%"></span></span><span class="v">${Math.round(A[i]*100)}</span></div>`).join("");
  const dm=$("dMeter"); if (dm){ dm.style.width=Math.round(A[selected]*100)+"%"; $("dVal").textContent=Math.round(A[selected]*100); }
  $("hudSel").textContent = `${REG[selected].k} · ${Math.round(A[selected]*100)}%`;
}

function renderStimButtons(){
  $("stimBtns").innerHTML = Object.entries(STIM).map(([k,s])=>`<button class="btn" data-s="${k}"><b>${s.t}</b><span class="small muted">${s.d}</span></button>`).join("");
  $("stimBtns").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{ stimulus(b.dataset.s); refresh(); }));
  $("sayForm").addEventListener("submit",e=>{ e.preventDefault(); const v=$("sayInput").value.trim(); if(!v) return; stimulus(parseText(v), v); $("sayInput").value=""; refresh(); });
}
function renderKnobs(){
  $("presets").innerHTML = Object.keys(PRESETS).map(p=>`<button data-p="${p}" class="${S.preset===p?"on":""}">${p}</button>`).join("");
  $("presets").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{ S.preset=b.dataset.p; S.P={...PRESETS[b.dataset.p]}; log("leer",`Character switched to ${b.dataset.p}.`); renderKnobs(); }));
  $("sliders").innerHTML = KNOBS.map(([k,l])=>`<div class="slider"><label for="k-${k}">${l}</label><input type="range" min="0" max="1" step="0.05" id="k-${k}" value="${S.P[k]}"><span class="px small" id="kv-${k}">${S.P[k].toFixed(2)}</span></div>`).join("");
  KNOBS.forEach(([k])=>$("k-"+k).addEventListener("input",e=>{ S.P[k]=+e.target.value; $("kv-"+k).textContent=S.P[k].toFixed(2); S.preset="custom"; $("presets").querySelectorAll("button").forEach(b=>b.classList.remove("on")); }));
}
let speed=1, paused=false;
function renderSpeeds(){
  $("speeds").innerHTML = [1,10,60].map(s=>`<button data-v="${s}" class="${speed===s?"on":""}">${s}x</button>`).join("");
  $("speeds").querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{ speed=+b.dataset.v; renderSpeeds(); }));
}
function toast(t){ $("toast").textContent=t; clearTimeout(toast.h); toast.h=setTimeout(()=>$("toast").textContent="",4000); }
let dbState = "starting storage...";
let savedCount = 0;
function renderData(){
  $("dataLine").textContent = `${EVENTS.length} events this session · ${S.counts.acties} actions and ${S.counts.prikkels} stimuli in total · ${dbState}${savedCount?` · saved ${savedCount} times`:""}`;
}
function refresh(){ renderNow(); renderNeeds(); renderData(); }

/* ============ TABS ============ */
function route(){
  const sim = location.hash==="#simulation";
  $("tab-brein").hidden = sim; $("tab-sim").hidden = !sim;
  $("t-brein").toggleAttribute("aria-current", !sim); if(!sim) $("t-brein").setAttribute("aria-current","page");
  $("t-sim").toggleAttribute("aria-current", sim); if(sim) $("t-sim").setAttribute("aria-current","page");
  $("simRow2").style.display = sim ? "" : "none";
  setTimeout(resize,0);
}
window.addEventListener("hashchange",route);

/* ============ 3D ============ */
const stage=$("stage"), labelsEl=$("labels");
let renderer, scene, camera, group, nodeMeshes=[], edgeObjs=[], pulses=[], labelEls=[];
let rotY=.6, rotX=.15, dist=5.2, autoRotate=true, showLabels=true;
const C_PAPER=new THREE.Color("#f8f4ea"), C_SKY=new THREE.Color("#8cc0e8"), C_EVA=new THREE.Color("#1b2a8c"), C_RED=new THREE.Color("#d7261e");
function heat(a){
  const c=new THREE.Color();
  if (a<.33) c.copy(C_PAPER).lerp(C_SKY,a/.33);
  else if (a<.7) c.copy(C_SKY).lerp(C_EVA,(a-.33)/.37);
  else c.copy(C_EVA).lerp(C_RED,(a-.7)/.3);
  return c;
}
function init3D(){
  if (!window.THREE){ stage.insertAdjacentHTML("beforeend","<p style='padding:20px'>Three.js did not load. The simulation keeps running.</p>"); return; }
  renderer = new THREE.WebGLRenderer({antialias:true, alpha:true});
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio||1));
  stage.prepend(renderer.domElement);
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(38,1,.1,100);
  scene.add(new THREE.HemisphereLight(0xffffff,0xb8ab92,.95));
  const dl=new THREE.DirectionalLight(0xffffff,.5); dl.position.set(3,5,4); scene.add(dl);
  group = new THREE.Group(); scene.add(group);
  // hersenschors: twee hemisferen, low-poly
  const shellMat = new THREE.MeshLambertMaterial({color:0xefe9dc, transparent:true, opacity:.16, flatShading:true, depthWrite:false, side:THREE.DoubleSide});
  const wireMat = new THREE.LineBasicMaterial({color:0x8a8070, transparent:true, opacity:.18});
  function blob(sx,sy,sz,x,y,z,detail){
    const g=new THREE.IcosahedronGeometry(1,detail);
    const pos=g.attributes.position;
    for (let i=0;i<pos.count;i++){ // klein beetje kreukels
      const v=new THREE.Vector3().fromBufferAttribute(pos,i);
      const n=1+.05*Math.sin(v.x*7)*Math.cos(v.y*6+v.z*5);
      pos.setXYZ(i,v.x*n,v.y*n,v.z*n);
    }
    g.computeVertexNormals();
    const m=new THREE.Mesh(g,shellMat); m.scale.set(sx,sy,sz); m.position.set(x,y,z);
    const w=new THREE.LineSegments(new THREE.WireframeGeometry(g),wireMat); w.scale.copy(m.scale); w.position.copy(m.position);
    group.add(m); group.add(w);
  }
  blob(1.8,1.2,.78, .1,.15, .55,2);
  blob(1.8,1.2,.78, .1,.15,-.55,2);
  blob(.6,.38,.85, 1.15,-.8,0,1);
  const stem=new THREE.Mesh(new THREE.CylinderGeometry(.16,.12,.9,8),shellMat); stem.position.set(.55,-1.15,0); stem.rotation.z=.3; group.add(stem);
  // regio's
  REG.forEach((r,i)=>{
    const m=new THREE.Mesh(new THREE.IcosahedronGeometry(.085,1), new THREE.MeshLambertMaterial({color:0xf8f4ea, flatShading:true, emissive:0x000000}));
    m.position.set(...r.p); m.userData.i=i; group.add(m); nodeMeshes.push(m);
    const halo=new THREE.Mesh(new THREE.SphereGeometry(.16,12,10), new THREE.MeshBasicMaterial({color:0xd7261e, transparent:true, opacity:0, depthWrite:false}));
    m.add(halo); m.userData.halo=halo;
    const l=document.createElement("div"); l.className="lbl"; l.textContent=r.k; labelsEl.appendChild(l); labelEls.push(l);
  });
  // verbindingen als bogen
  EDGES.forEach(e=>{
    const a=new THREE.Vector3(...REG[e.a].p), b=new THREE.Vector3(...REG[e.b].p);
    const mid=a.clone().add(b).multiplyScalar(.5);
    const out=mid.clone().setLength(mid.length()+.18+a.distanceTo(b)*.12);
    const curve=new THREE.QuadraticBezierCurve3(a,out,b);
    const geo=new THREE.BufferGeometry().setFromPoints(curve.getPoints(18));
    const mat=new THREE.LineBasicMaterial({color:e.w<0?0xd7261e:0x1b2a8c, transparent:true, opacity:.12});
    const line=new THREE.Line(geo,mat); group.add(line);
    edgeObjs.push({e,curve,mat,acc:0});
  });
  // signaalbolletjes
  const pg=new THREE.SphereGeometry(.028,6,5);
  for (let i=0;i<220;i++){
    const m=new THREE.Mesh(pg,new THREE.MeshBasicMaterial({color:0x1b2a8c})); m.visible=false; group.add(m);
    pulses.push({m,on:false,t:0,curve:null,spd:0});
  }
  // besturing
  let down=null, moved=false;
  stage.addEventListener("pointerdown",ev=>{ down={x:ev.clientX,y:ev.clientY,ry:rotY,rx:rotX}; moved=false; stage.classList.add("drag"); stage.setPointerCapture(ev.pointerId); });
  stage.addEventListener("pointermove",ev=>{ if(!down) return; const dx=ev.clientX-down.x, dy=ev.clientY-down.y; if(Math.abs(dx)+Math.abs(dy)>4) moved=true; rotY=down.ry+dx*.008; rotX=clamp(down.rx+dy*.006,-1.2,1.2); });
  stage.addEventListener("pointerup",ev=>{ stage.classList.remove("drag"); if(down && !moved) pickAt(ev); down=null; });
  stage.addEventListener("wheel",ev=>{ ev.preventDefault(); dist=clamp(dist+ev.deltaY*.003,3,9); },{passive:false});
  window.addEventListener("resize",resize); resize();
  requestAnimationFrame(frame);
}
const ray=new THREE.Raycaster(), mv=new THREE.Vector2();
function pickAt(ev){
  const r=renderer.domElement.getBoundingClientRect();
  mv.x=((ev.clientX-r.left)/r.width)*2-1; mv.y=-((ev.clientY-r.top)/r.height)*2+1;
  ray.setFromCamera(mv,camera);
  const hit=ray.intersectObjects(nodeMeshes,false)[0];
  if (hit){ select(hit.object.userData.i); if (location.hash==="#simulation") toast(`${REG[selected].n}: see the brain tab for what it does.`); }
}
function resize(){
  if(!renderer) return;
  const w=stage.clientWidth, h=stage.clientHeight;
  renderer.setSize(w,h); camera.aspect=w/h; camera.updateProjectionMatrix();
}
const tmpV=new THREE.Vector3();
let lastT=performance.now();
function frame(now){
  const dt=Math.min(.05,(now-lastT)/1000); lastT=now;
  if (autoRotate && !stage.classList.contains("drag")) rotY += dt*.12;
  group.rotation.set(rotX,rotY,0);
  camera.position.set(0,.15,dist); camera.lookAt(0,-.05,0);
  // knopen
  nodeMeshes.forEach((m,i)=>{
    const a=A[i];
    m.material.color.copy(heat(a));
    m.material.emissive.copy(heat(a)).multiplyScalar(a*.35);
    const s=1+a*1.1+(i===selected?.35:0); m.scale.setScalar(s);
    m.userData.halo.material.opacity = i===selected ? .22 : a>.7 ? (a-.7)*.6 : 0;
    m.userData.halo.material.color.set(i===selected?0xd7261e:0x8cc0e8);
  });
  // lijnen en signalen
  edgeObjs.forEach(o=>{
    const flow=A[o.e.a]*Math.abs(o.e.w);
    const hl = (o.e.a===selected||o.e.b===selected);
    o.mat.opacity = clamp(.07 + flow*.9 + (hl?.25:0), 0, .95);
    o.acc += flow*dt*speedFactor()*3.2;
    if (o.acc>1){ o.acc-=1; spawnPulse(o); }
  });
  pulses.forEach(p=>{
    if(!p.on) return;
    p.t += dt*p.spd;
    if (p.t>=1){ p.on=false; p.m.visible=false; return; }
    p.curve.getPoint(p.t,tmpV); p.m.position.copy(tmpV);
  });
  renderer.render(scene,camera);
  // labels
  const w=stage.clientWidth, h=stage.clientHeight;
  nodeMeshes.forEach((m,i)=>{
    const el=labelEls[i];
    if (!showLabels && i!==selected){ el.style.display="none"; return; }
    m.getWorldPosition(tmpV); tmpV.project(camera);
    if (tmpV.z>1){ el.style.display="none"; return; }
    el.style.display="block";
    el.style.left=((tmpV.x+1)/2*w)+"px"; el.style.top=((1-tmpV.y)/2*h)+"px";
    el.classList.toggle("sel", i===selected);
    el.style.opacity = i===selected ? 1 : (.45 + A[i]*.55);
  });
  requestAnimationFrame(frame);
}
function speedFactor(){ return paused ? .15 : Math.min(3, .6+Math.log10(speed)*.9); }
function spawnPulse(o){
  const p=pulses.find(x=>!x.on); if(!p) return;
  p.on=true; p.t=0; p.curve=o.curve; p.spd=.9+Math.random()*.6; p.m.visible=true;
  p.m.material.color.set(o.e.w<0?0xd7261e:0x1b2a8c);
}

/* ============ OPSLAG ============ */
// His state stays in this browser (localStorage), so he carries on where he was.
// The log goes to Supabase in batches (table sim_log, insert only), if that table exists.
const LS_KEY="grimsby-sim-v1";
let sb=null, clientId="";
function stateDoc(){ return {state:JSON.stringify(S), saved:Date.now(), t:S.t}; }
function initStorage(){
  try{
    clientId = localStorage.getItem("grimsby-sim-client") || (Math.random().toString(36).slice(2)+Date.now().toString(36));
    localStorage.setItem("grimsby-sim-client", clientId);
    const raw = localStorage.getItem(LS_KEY);
    if (raw){
      const d = JSON.parse(raw), loaded = JSON.parse(d.state);
      if (loaded && loaded.v===1){
        const pauseMin = Math.round((Date.now()-(d.saved||Date.now()))/60000);
        S = Object.assign(freshState(), loaded);
        renderKnobs();
        log("actie", `Carrying on where he was. The page was closed for ${pauseMin} minutes, and his brain stood still.`);
      }
    }
    dbState = "state kept in this browser";
  }catch(e){ dbState = "no storage in this browser"; }
  try{
    const cfg = window.GRIMSBY_CONFIG && window.GRIMSBY_CONFIG.supabase;
    if (cfg && window.supabase){
      sb = window.supabase.createClient(cfg.url, cfg.key, {global:{headers:{"x-grimsby-client":clientId}}, auth:{persistSession:false}});
      dbState += " · log goes to Supabase";
    }
  }catch(e){ sb=null; }
  renderData();
  setInterval(flush, 30000);
}
let flushing=false, sbBroken=false, lastSb=Date.now();
async function flush(){
  try{ localStorage.setItem(LS_KEY, JSON.stringify(stateDoc())); }catch(e){}
  const due = Date.now()-lastSb > 300000 || PENDING.length >= 400;   // at most every 5 minutes to Supabase
  if (!sb || sbBroken || flushing || !PENDING.length || !due){ savedCount++; renderData(); return; }
  lastSb = Date.now();
  flushing=true;
  const batch = PENDING.splice(0, 400);
  try{
    const {error} = await sb.from("sim_log").insert({client:clientId, preset:S.preset, sim_from:batch[0].t, sim_to:batch[batch.length-1].t, n:batch.length, events:batch});
    if (error){ PENDING.unshift(...batch); if (/relation|does not exist|schema cache|permission/i.test(error.message)) { sbBroken=true; dbState="state kept in this browser · Supabase table missing"; } }
    else savedCount++;
  }catch(e){ PENDING.unshift(...batch); }
  if (PENDING.length>4000) PENDING.splice(0, PENDING.length-4000);
  flushing=false; renderData();
}
function exportJSON(){ return JSON.stringify({state:S, events:EVENTS}, null, 1); }

/* ============ KNOPPEN ============ */
$("bLabels").addEventListener("click",e=>{ showLabels=!showLabels; e.currentTarget.setAttribute("aria-pressed",showLabels); });
$("bRotate").addEventListener("click",e=>{ autoRotate=!autoRotate; e.currentTarget.setAttribute("aria-pressed",autoRotate); });
$("bPause").addEventListener("click",e=>{ paused=!paused; e.currentTarget.setAttribute("aria-pressed",paused); e.currentTarget.textContent=paused?"resume":"pause"; $("liveDot").classList.toggle("off",paused); });
$("bExport").addEventListener("click",()=>{
  try{
    const url=URL.createObjectURL(new Blob([exportJSON()],{type:"application/json"}));
    const a=document.createElement("a"); a.href=url; a.download=`grimsby-${fmtTime(S.t).replace(/[^0-9a-z]+/gi,"-")}.json`;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),2000);
    toast("Download started.");
  }catch(e){ toast("Downloading does not work in this browser."); }
});
$("bCopy").addEventListener("click",async()=>{
  try{ await navigator.clipboard.writeText(exportJSON()); toast(`${EVENTS.length} events copied.`); }
  catch(e){ toast("Copying does not work here."); }
});
let resetArmed=false;
$("bReset").addEventListener("click",e=>{
  if(!resetArmed){ resetArmed=true; e.currentTarget.textContent="sure?"; setTimeout(()=>{resetArmed=false; $("bReset").textContent="start over";},3000); return; }
  resetArmed=false; e.currentTarget.textContent="start over";
  S=freshState(); EVENTS=[]; PENDING=[]; $("feed").innerHTML=""; A.fill(0); renderKnobs(); log("actie","New brain. Everything forgotten. He does not even know the AH exists."); flush(); refresh();
});

/* ============ START ============ */
renderStimButtons(); renderKnobs(); renderSpeeds(); renderDetail(); route();
log("actie","Awake at the playground.");
init3D();
setInterval(()=>{ if(paused) return; for(let i=0;i<speed;i++) tick(); refresh(); }, 1000);
initStorage();
window.addEventListener("pagehide",()=>{ flush(); });
document.addEventListener("visibilitychange",()=>{ if(document.hidden) flush(); });
