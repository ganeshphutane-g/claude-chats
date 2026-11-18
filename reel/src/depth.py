from PIL import Image, ImageDraw, ImageFilter
import sys
A="art/"  # put the downloaded source paintings here
def mk(name, size, build, blur=18, maxh=2300):
    im=Image.open(A+name+".jpg").convert("RGB")
    if im.height>maxh: im=im.resize((int(im.width*maxh/im.height),maxh),Image.LANCZOS)
    im.save(f"tex/{name}.jpg",quality=93)
    W,H=320,int(320*im.height/im.width)
    d=Image.new("L",(W,H),0); dr=ImageDraw.Draw(d)
    def grad(y0,y1,v0,v1):
        for y in range(int(y0*H),int(y1*H)):
            f=(y/H-y0)/max(1e-6,(y1-y0)); dr.line([(0,y),(W,y)],fill=int(255*(v0+(v1-v0)*f)))
    def poly(pts,v): dr.polygon([(x*W,y*H) for x,y in pts],fill=int(255*v))
    def ell(x0,y0,x1,y1,v): dr.ellipse([x0*W,y0*H,x1*W,y1*H],fill=int(255*v))
    build(grad,poly,ell)
    d=d.filter(ImageFilter.GaussianBlur(blur*W/320)); d.save(f"tex/{name}_d.png"); print(name,im.size)
def wanderer(g,p,e):
    g(0,.42,.03,.08); g(.42,1,.22,.5)
    e(.06,.5,.34,.68,.5); e(.6,.5,.92,.62,.42)
    p([(0,1),(0,.9),(.2,.72),(.33,.67),(.5,.62),(.62,.66),(.72,.8),(.9,.85),(1,.9),(1,1)],.9)
    p([(.42,.35),(.6,.35),(.6,.7),(.4,.7)],1.0); e(.44,.31,.54,.4,1.0)
def lark(g,p,e):
    g(0,.36,.03,.06); g(.36,1,.22,.8)
    p([(.56,.2),(.7,.2),(.76,.5),(.74,.93),(.56,.93),(.53,.5)],1.0); e(.57,.13,.69,.26,1.0)
def wood(g,p,e):
    g(0,.2,.03,.05); g(.2,.6,.15,.2); g(.6,1,.4,.8)
    e(0,.42,.36,.78,.6); p([(.34,.3),(.56,.22),(.6,.5),(.56,.88),(.33,.88)],1.0)
def milton(g,p,e):
    g(0,1,.08,.2)
    e(.03,.35,.32,.95,.8); e(.56,.22,.92,.9,.65); p([(.34,.25),(.54,.2),(.56,.6),(.5,.97),(.12,.97),(.3,.6)],1.0)
def jatte(g,p,e):
    g(0,.3,.05,.1); g(.3,1,.15,.8)
    p([(.71,.1),(.9,.1),(.9,.97),(.71,.97)],1.0); e(.03,.6,.3,.92,.85)
mk("wanderer",0,wanderer); mk("lark",0,lark); mk("woodchopper",0,wood); mk("milton",0,milton,blur=22); mk("jatte",0,jatte)
