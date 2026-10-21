"""Render the current PDF for visual inspection, replacing stale preview images."""
from pathlib import Path
import pymupdf
from PIL import Image, ImageDraw

WORK=Path(__file__).resolve().parents[1]
preview=WORK/'report/preview';preview.mkdir(exist_ok=True)
with pymupdf.open(WORK/'report/Chuong_2.pdf') as doc:
    thumbs=[]
    for i in range(len(doc)):
        page=doc.load_page(i)
        pix=page.get_pixmap(matrix=pymupdf.Matrix(.6,.6))
        im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        thumb=Image.new('RGB',(im.width+10,im.height+30),'#dddddd')
        thumb.paste(im,(5,25));ImageDraw.Draw(thumb).text((5,5),f'Page {i+1}',fill='black');thumbs.append(thumb)
        if i in [0,3,7]:page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(preview/f'page_{i+1:02d}.png')
    w=max(im.width for im in thumbs);h=max(im.height for im in thumbs)
    contact=Image.new('RGB',(w*5,h*((len(thumbs)+4)//5)),'#eeeeee')
    for i,im in enumerate(thumbs):contact.paste(im,((i%5)*w,(i//5)*h))
    contact.save(preview/'contact_sheet.png')
    print('Preview refreshed for',len(doc),'PDF pages.')
