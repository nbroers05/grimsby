"use strict";
/* The 3D brain, as a view on a running simulation. Used by index.html (big, in brein.js) and by the small
   brain in world.html (which lives in an iframe of index.html and reads the same simulation from parent.GRIM).
   makeBrainView({THREE, stage, labelsEl, sim, getSelected, onSelect, camDist, opts}) -> {resize, setLabels, setRotate}
   sim = {REG, EDGES, A, speedFactor()}: whatever runs the brain; the view only reads it. */
function makeBrainView(o){
  const THREE=o.THREE, stage=o.stage, labelsEl=o.labelsEl, sim=o.sim, REG=sim.REG, EDGES=sim.EDGES, A=sim.A;
  const getSelected=o.getSelected||(()=>-1), onSelect=o.onSelect||(()=>{});
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  if (!THREE){ stage.insertAdjacentHTML("beforeend","<p style='padding:20px'>Three.js did not load. The simulation keeps running.</p>"); return {resize(){},setLabels(){},setRotate(){}}; }
  const renderer=new THREE.WebGLRenderer({antialias:true, alpha:true});
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio||1));
  stage.prepend(renderer.domElement);
  const scene=new THREE.Scene();
  const camera=new THREE.PerspectiveCamera(38,1,.1,100);
  scene.add(new THREE.HemisphereLight(0xffffff,0xb8ab92,.95));
  const dl=new THREE.DirectionalLight(0xffffff,.5); dl.position.set(3,5,4); scene.add(dl);
  const group=new THREE.Group(); scene.add(group);
  const nodeMeshes=[], edgeObjs=[], pulses=[], labelEls=[];
  let rotY=.6, rotX=.15, dist=o.camDist||5.2, autoRotate=true, showLabels=o.labels!==false;
  const C_PAPER=new THREE.Color("#f8f4ea"), C_SKY=new THREE.Color("#8cc0e8"), C_EVA=new THREE.Color("#1b2a8c"), C_RED=new THREE.Color("#d7261e");
  const heatC=new THREE.Color();
  function heat(a){
    const c=heatC;
    if (a<.33) c.copy(C_PAPER).lerp(C_SKY,a/.33);
    else if (a<.7) c.copy(C_SKY).lerp(C_EVA,(a-.33)/.37);
    else c.copy(C_EVA).lerp(C_RED,(a-.7)/.3);
    return c;
  }
  // brain shell: two hemispheres, low-poly
  const shellMat=new THREE.MeshLambertMaterial({color:0xefe9dc, transparent:true, opacity:.16, flatShading:true, depthWrite:false, side:THREE.DoubleSide});
  const wireMat=new THREE.LineBasicMaterial({color:0x8a8070, transparent:true, opacity:.18});
  function blob(sx,sy,sz,x,y,z,detail){
    const g=new THREE.IcosahedronGeometry(1,detail);
    const pos=g.attributes.position;
    for (let i=0;i<pos.count;i++){
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
  REG.forEach((r,i)=>{
    const m=new THREE.Mesh(new THREE.IcosahedronGeometry(.085,1), new THREE.MeshLambertMaterial({color:0xf8f4ea, flatShading:true, emissive:0x000000}));
    m.position.set(...r.p); m.userData.i=i; group.add(m); nodeMeshes.push(m);
    const halo=new THREE.Mesh(new THREE.SphereGeometry(.16,12,10), new THREE.MeshBasicMaterial({color:0xd7261e, transparent:true, opacity:0, depthWrite:false}));
    m.add(halo); m.userData.halo=halo;
    const l=document.createElement("div"); l.className="lbl"; l.textContent=r.k; labelsEl.appendChild(l); labelEls.push(l);
  });
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
  const pg=new THREE.SphereGeometry(.028,6,5);
  for (let i=0;i<220;i++){
    const m=new THREE.Mesh(pg,new THREE.MeshBasicMaterial({color:0x1b2a8c})); m.visible=false; group.add(m);
    pulses.push({m,on:false,t:0,curve:null,spd:0});
  }
  // controls
  let down=null, moved=false;
  const ray=new THREE.Raycaster(), mv=new THREE.Vector2();
  function pickAt(ev){
    const r=renderer.domElement.getBoundingClientRect();
    mv.x=((ev.clientX-r.left)/r.width)*2-1; mv.y=-((ev.clientY-r.top)/r.height)*2+1;
    ray.setFromCamera(mv,camera);
    const hit=ray.intersectObjects(nodeMeshes,false)[0];
    if (hit) onSelect(hit.object.userData.i);
  }
  stage.addEventListener("pointerdown",ev=>{ down={x:ev.clientX,y:ev.clientY,ry:rotY,rx:rotX}; moved=false; stage.classList.add("drag"); stage.setPointerCapture(ev.pointerId); });
  stage.addEventListener("pointermove",ev=>{ if(!down) return; const dx=ev.clientX-down.x, dy=ev.clientY-down.y; if(Math.abs(dx)+Math.abs(dy)>4) moved=true; rotY=down.ry+dx*.008; rotX=clamp(down.rx+dy*.006,-1.2,1.2); });
  stage.addEventListener("pointerup",ev=>{ stage.classList.remove("drag"); if(down && !moved) pickAt(ev); down=null; });
  stage.addEventListener("wheel",ev=>{ ev.preventDefault(); dist=clamp(dist+ev.deltaY*.003,3,9); },{passive:false});
  function resize(){
    const w=stage.clientWidth, h=stage.clientHeight;
    if (!w || !h) return;                       // hidden tab: nothing to size
    renderer.setSize(w,h); camera.aspect=w/h; camera.updateProjectionMatrix();
  }
  window.addEventListener("resize",resize);
  if (window.ResizeObserver) new ResizeObserver(resize).observe(stage);
  resize();
  const tmpV=new THREE.Vector3();
  let lastT=performance.now();
  function spawnPulse(q){
    const p=pulses.find(x=>!x.on); if(!p) return;
    p.on=true; p.t=0; p.curve=q.curve; p.spd=.9+Math.random()*.6; p.m.visible=true;
    p.m.material.color.set(q.e.w<0?0xd7261e:0x1b2a8c);
  }
  function frame(now){
    requestAnimationFrame(frame);
    const dt=Math.min(.05,(now-lastT)/1000); lastT=now;
    const w=stage.clientWidth, h=stage.clientHeight;
    if (!w || !h) return;                       // not visible (other tab): skip drawing, keep the loop alive
    const selected=getSelected();
    if (autoRotate && !stage.classList.contains("drag")) rotY += dt*.12;
    group.rotation.set(rotX,rotY,0);
    camera.position.set(0,.15,dist); camera.lookAt(0,-.05,0);
    nodeMeshes.forEach((m,i)=>{
      const a=A[i];
      m.material.color.copy(heat(a));
      m.material.emissive.copy(heat(a)).multiplyScalar(a*.35);
      m.scale.setScalar(1+a*1.1+(i===selected?.35:0));
      m.userData.halo.material.opacity = i===selected ? .22 : a>.7 ? (a-.7)*.6 : 0;
      m.userData.halo.material.color.set(i===selected?0xd7261e:0x8cc0e8);
    });
    const sf=sim.speedFactor();
    edgeObjs.forEach(q=>{
      const flow=A[q.e.a]*Math.abs(q.e.w);
      const hl=(q.e.a===selected||q.e.b===selected);
      q.mat.opacity=clamp(.07+flow*.9+(hl?.25:0),0,.95);
      q.acc += flow*dt*sf*3.2;
      if (q.acc>1){ q.acc-=1; spawnPulse(q); }
    });
    pulses.forEach(p=>{
      if(!p.on) return;
      p.t += dt*p.spd;
      if (p.t>=1){ p.on=false; p.m.visible=false; return; }
      p.curve.getPoint(p.t,tmpV); p.m.position.copy(tmpV);
    });
    renderer.render(scene,camera);
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
  }
  requestAnimationFrame(frame);
  return { resize, setLabels(v){ showLabels=v; }, setRotate(v){ autoRotate=v; } };
}
