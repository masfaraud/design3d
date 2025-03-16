# -*- coding: utf-8 -*-
"""

"""

import design3d as vm
import design3d.wires as vmw

list_point3d = [vm.Point3D(-0.5178099145507813, 0.3835421110454358, 0.3857924987792969),
                vm.Point3D(-0.5197773189544678, 0.3835421110454358, 0.5413672103881836),
                vm.Point3D(-0.5304534708658855, 0.3835421110454358, 0.5678178168402778),
                vm.Point3D(-0.5330403064546132, 0.3835421110454358, 0.5746585751488096),
                vm.Point3D(-0.5350836070667614, 0.3835421110454358, 0.586832597212358),
                vm.Point3D(-0.5319884033203125, 0.3835421110454358, 0.6015205688476563),
                vm.Point3D(-0.5160523885091146, 0.3835421110454358, 0.6115547180175782),
                vm.Point3D(-0.5112239227294921, 0.3835421110454358, 0.6141255493164063),
                vm.Point3D(-0.5024894409179688, 0.3835421110454358, 0.6169224940708705),
                vm.Point3D(-0.4358712565104167, 0.3835421110454358, 0.620560567220052),
                vm.Point3D(-0.4239801920572917, 0.3835421110454358, 0.6202111165364583),
                vm.Point3D(-0.4103144683837891, 0.3835421110454358, 0.6152636184692383),
                vm.Point3D(-0.40744049835205076, 0.3835421110454358, 0.6150783081054687),
                vm.Point3D(-0.33904239654541013, 0.3835421110454358, 0.6254386215209962),
                vm.Point3D(-0.2765469767252604, 0.3835421110454358, 0.5992764078776042),
                vm.Point3D(-0.27408895874023437, 0.3835421110454358, 0.6011351928710937),
                vm.Point3D(-0.2704830780029297, 0.3835421110454358, 0.6035126342773438),
                vm.Point3D(-0.26985113525390625, 0.3835421110454358, 0.6038867797851563),
                vm.Point3D(-0.2664568176269531, 0.3835421110454358, 0.6052403564453125),
                vm.Point3D(-0.2550249464246962, 0.3835421110454358, 0.6086328938802084),
                vm.Point3D(-0.23500917434692384, 0.3835421110454358, 0.6141721496582031),
                vm.Point3D(-0.2051714204152425, 0.3835421110454358, 0.6166307957967122),
                vm.Point3D(-0.14391629028320313, 0.3835421110454358, 0.6294749755859376),
                vm.Point3D(-0.1418434997558594, 0.3835421110454358, 0.6330667236328126),
                vm.Point3D(-0.13987664031982422, 0.3835421110454358, 0.6356470642089844),
                vm.Point3D(-0.138427978515625, 0.3835421110454358, 0.6373294677734375),
                vm.Point3D(-0.1355097198486328, 0.3835421110454358, 0.6394069213867187),
                vm.Point3D(-0.03984661865234375, 0.3835421110454358, 0.6958330078125),
                vm.Point3D(-0.027353710174560546, 0.3835421110454358, 0.6940150146484375),
                vm.Point3D(-0.017186071395874025, 0.3835421110454358, 0.6765811767578125),
                vm.Point3D(-0.016856738249460858, 0.3835421110454358, 0.6756893107096354),
                vm.Point3D(-0.014887657165527344, 0.3835421110454358, 0.6684420776367188),
                vm.Point3D(-0.01493448407309396, 0.3835421110454358, 0.6673169642857143),
                vm.Point3D(-0.015307965087890625, 0.3835421110454358, 0.6605929443359375),
                vm.Point3D(-0.047395610173543296, 0.3835421110454358, 0.5393658548990885),
                vm.Point3D(-0.047534745758655024, 0.3835421110454358, 0.5383761728324142),
                vm.Point3D(-0.0433504467010498, 0.3835421110454358, 0.5155026245117188),
                vm.Point3D(-0.04582256158192953, 0.3835421110454358, 0.4937494862874349),
                vm.Point3D(-0.046309296607971194, 0.3835421110454358, 0.4918007965087891),
                vm.Point3D(-0.05913432312011719, 0.3835421110454358, 0.46303253173828124),
                vm.Point3D(-0.0942486343383789, 0.3835421110454358, 0.4086387939453125),
                vm.Point3D(-0.10980977630615235, 0.3835421110454358, 0.3776604309082031),
                vm.Point3D(-0.10323926798502604, 0.3835421110454358, 0.2641988525390625),
                vm.Point3D(-0.10429043579101563, 0.3835421110454358, 0.2533271115620931),
                vm.Point3D(-0.03381659889221191, 0.3835421110454358, 0.15340726470947266),
                vm.Point3D(-0.02781885363260905, 0.3835421110454358, 0.14346873881022137),
                vm.Point3D(-0.024167933464050294, 0.3835421110454358, 0.12982427215576173),
                vm.Point3D(-0.023739212209528144, 0.3835421110454358, 0.11562704814564098),
                vm.Point3D(-0.028338952064514162, 0.3835421110454358, 0.10941262708391462),
                vm.Point3D(-0.03655623765425249, 0.3835421110454358, 0.10293642702969638),
                vm.Point3D(-0.044855001661512586, 0.3835421110454358, 0.09876531643337674),
                vm.Point3D(-0.05405003063495342, 0.3835421110454358, 0.0956848126924955),
                vm.Point3D(-0.05691987133026123, 0.3835421110454358, 0.09481699371337891),
                vm.Point3D(-0.06988954544067383, 0.3835421110454358, 0.10127440452575684),
                vm.Point3D(-0.08239832364595853, 0.3835421110454358, 0.10782138883150541),
                vm.Point3D(-0.16314332580566407, 0.3835421110454358, 0.1003914680480957),
                vm.Point3D(-0.16888108171735491, 0.3835421110454358, 0.09392223576136999), 
                vm.Point3D(-0.2154586460508149, 0.3835421110454358, 0.06878548457704742), 
                vm.Point3D(-0.22443978118896485, 0.3835421110454358, 0.06694517135620118), 
                vm.Point3D(-0.39464658490349264, 0.3835421110454358, 0.09343803001852596), 
                vm.Point3D(-0.48124072265625, 0.3835421110454358, 0.1158543955485026), 
                vm.Point3D(-0.5003765627838844, 0.3835421110454358, 0.14312240813499275), 
                vm.Point3D(-0.5061948980287064, 0.3835421110454358, 0.15310074917105743), 
                vm.Point3D(-0.5241014404296875, 0.3835421110454358, 0.20350949096679688), 
                vm.Point3D(-0.5384811471623483, 0.3835421110454358, 0.2944790273981986), 
                vm.Point3D(-0.5409509887695313, 0.3835421110454358, 0.31459671738568473)]

poly = vmw.ClosedPolygon3D(list_point3d)


ax = poly.plot()
for pt in list_point3d :
    pt.plot(ax=ax)
    
simpoly = poly.simplify(0.1, 0.2)
simpoly.plot(ax=ax, color='g')
for pt, pt2 in zip(simpoly.points, simpoly.points[1:]+[simpoly.points[0]]) :
    pt.plot(ax=ax, color='g')
    print(pt.point_distance(pt2))
