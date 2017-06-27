import bpy
import math
from .rftool import RFTool
from .rfwidget_circle import RFWidget_Circle
from ..common.maths import Point,Point2D,Vec2D,Vec

class RFTool_Tweak_Relax(RFTool):
    ''' Called when RetopoFlow is started, but not necessarily when the tool is used '''
    def init(self):
        self.FSM['relax'] = self.modal_relax
        self.FSM['resize'] = lambda: RFWidget_Circle().modal_resize('main')
        self.FSM['restrength'] = lambda: RFWidget_Circle().modal_restrength('main')
    
    ''' Called the tool is being switched into '''
    def start(self):
        RFWidget_Circle().color = (0.5, 1.0, 0.5)
    
    ''' Returns type of cursor to display '''
    def rfwidget(self):
        return RFWidget_Circle()
    
    def modal_main(self):
        if self.rfcontext.eventd.press in self.rfcontext.keymap['action']:
            self.rfcontext.undo_push('tweak relax')
            self.rfcontext.ensure_lookup_tables()
            return 'relax'
        
        if self.rfcontext.eventd.press in self.rfcontext.keymap['brush size']:
            return 'resize'
        
        if self.rfcontext.eventd.press in self.rfcontext.keymap['brush strength']:
            return 'restrength'
    
    @RFTool.dirty_when_done
    def modal_relax(self):
        if self.rfcontext.eventd.release in self.rfcontext.keymap['action']:
            return 'main'
        if self.rfcontext.eventd.release in self.rfcontext.keymap['cancel']:
            self.rfcontext.undo_cancel()
            return 'main'
        
        if self.rfcontext.eventd.type not in {'TIMER'}: return
        
        hit_pos = self.rfcontext.hit_pos
        if not hit_pos: return
        
        radius = RFWidget_Circle().get_scaled_radius()
        nearest = self.rfcontext.target_nearest_bmverts_Point(hit_pos, radius)
        self.rfcontext.select([bmv for bmv,_ in nearest])
        
        avgDist,avgCount,divco = 0,0,{}
        
        # collect data for smoothing
        for bmv0,d in nearest:
            lbme,lbmf = bmv0.link_edges, bmv0.link_faces
            avgDist += sum(bme.calc_length() for bme in lbme)
            avgCount += len(lbme)
            divco[bmv0] = bmv0.co
            for bme in lbme:
                bmv1 = bme.other_vert(bmv0)
                divco[bmv1] = bmv1.co
            for bmf in lbmf:
                for bmv in bmf.verts:
                    divco[bmv] = bmv.co
        
        # bail if no data to smooth
        if avgCount == 0: return
        avgDist /= avgCount
        
        # perform smoothing
        for bmv0,d in nearest:
            lbme,lbmf = bmv0.link_edges, bmv0.link_faces
            if not lbme: continue
            for bme in bmv0.link_edges:
                bmv1 = bme.other_vert(bmv0)
                diff = (bmv1.co - bmv0.co)
                m = (avgDist - diff.length) * (1.0 - d) * 0.1
                divco[bmv1] += diff * m
            for bmf in lbmf:
                cnt = len(bmf.verts)
                ctr = sum([bmv.co for bmv in bmf.verts], Vec((0,0,0))) / cnt
                fd = sum((ctr-bmv.co).length for bmv in bmf.verts) / cnt
                for bmv in bmf.verts:
                    diff = (bmv.co - ctr)
                    m = (fd - diff.length)* (1.0- d) / cnt
                    divco[bmv] += diff * m
        
        # update
        for bmv,co in divco.items():
            p,_,_,_ = self.rfcontext.nearest_sources_Point(co)
            bmv.co = p
    