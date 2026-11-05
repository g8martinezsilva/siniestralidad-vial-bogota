"""Fondo cartográfico reproducible en Web Mercator para las figuras del informe.

Teselas OpenStreetMap: descarga única y caché local; no altera coordenadas.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageEnhance
import requests

R = 6378137.0
CACHE = Path(__file__).resolve().parents[2] / 'data' / 'external' / 'cache_cartografia'

def mercator(lon, lat):
    return R * np.radians(lon), R * np.log(np.tan(np.pi/4 + np.radians(lat)/2))

def fondo(ax, limites, zoom=12):
    """Dibuja teselas almacenadas, con atribución que debe conservarse al exportar."""
    xmin,xmax,ymin,ymax=limites
    total=2*math.pi*R; n=2**zoom
    xa=max(0,int((xmin+total/2)/total*n)); xb=min(n-1,int((xmax+total/2)/total*n))
    ya=max(0,int((total/2-ymax)/total*n)); yb=min(n-1,int((total/2-ymin)/total*n))
    CACHE.mkdir(parents=True,exist_ok=True)
    canvas=Image.new('RGB',((xb-xa+1)*256,(yb-ya+1)*256),'white')
    for x in range(xa,xb+1):
        for y in range(ya,yb+1):
            p=CACHE/f'osm_{zoom}_{x}_{y}.png'
            if not p.exists():
                response=requests.get(f'https://tile.openstreetmap.org/{zoom}/{x}/{y}.png',timeout=40,
                                      headers={'User-Agent':'SiniestralidadBogota/1.0 (academic map)'})
                response.raise_for_status(); p.write_bytes(response.content)
            with Image.open(p) as im: canvas.paste(im.convert('RGB'),((x-xa)*256,(y-ya)*256))
    extent=(xa/n*total-total/2,(xb+1)/n*total-total/2,total/2-(yb+1)/n*total,total/2-ya/n*total)
    canvas = ImageEnhance.Color(canvas).enhance(0.08)
    canvas = Image.blend(canvas, Image.new("RGB", canvas.size, "white"), .20)
    ax.imshow(canvas,extent=extent,zorder=0)
    ax.set_xlim(xmin,xmax); ax.set_ylim(ymin,ymax)
    ax.text(.01,.005,'© OpenStreetMap contributors',transform=ax.transAxes,fontsize=6.5,
            bbox=dict(facecolor='white',edgecolor='none',alpha=.9,pad=2),zorder=10)

def marco(ax, limites):
    xmin,xmax,ymin,ymax=limites
    ax.set_xlim(xmin,xmax); ax.set_ylim(ymin,ymax); ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    ax.annotate('N',xy=(.94,.96),xytext=(.94,.87),xycoords='axes fraction',ha='center',va='center',
                fontsize=11,fontweight='bold',arrowprops=dict(arrowstyle='-|>',color='#333333'),zorder=10)
    x=xmin+(xmax-xmin)*.06; y=ymin+(ymax-ymin)*.055
    ax.plot([x,x+5000],[y,y],color='#222222',lw=3,zorder=10)
    ax.text(x+2500,y+(ymax-ymin)*.012,'5 km',ha='center',fontsize=8,zorder=10,
            bbox=dict(facecolor='white',edgecolor='none',alpha=.85,pad=1))
