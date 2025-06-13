
from bjsp_download_ah import download_ah
from bjsp_download_bj import download_bj
from bjsp_download_cq import download_cq
from bjsp_download_fj import download_fj
from bjsp_download_gd import download_gd
from bjsp_download_gx import download_gx
from bjsp_download_gz import download_gz
from bjsp_download_hb import download_hb
from bjsp_download_hlj import download_hlj
from bjsp_download_hn import download_hn
# from bjsp_download_hub import download_hub
from bjsp_download_hun import download_hun
from bjsp_download_jl import download_jl
from bjsp_download_js import download_js
from bjsp_download_jx import download_jx
from bjsp_download_ln import download_ln
from bjsp_download_nmg import download_nmg
from bjsp_download_sc import download_sc
from bjsp_download_sd import download_sd
from bjsp_download_sh import download_sh
from bjsp_download_sx import download_sx  # 山西
from bjsp_download_shanxi2 import download_shanxi2  # 陕西
from bjsp_download_tj import download_tj
from bjsp_download_xj import download_xj
from bjsp_download_yn import download_yn

province_to_download_function = {
    '北京': download_bj,
    '天津': download_tj,
    '河北': download_hb,
    '山西': download_sx,
    '内蒙古': download_nmg,
    '辽宁': download_ln,
    '吉林': download_jl,
    '黑龙江': download_hlj,
    '上海': download_sh,
    '江苏': download_js,
    '安徽': download_ah,
    '福建': download_fj,
    '江西': download_jx,
    '山东': download_sd,
    '河南': download_hn,
    '湖南': download_hun,
    '广东': download_gd,
    '广西': download_gx,
    '重庆': download_cq,
    '四川': download_sc,
    '贵州': download_gz,
    '云南': download_yn,
    '陕西': download_shanxi2,
    '新疆': download_xj,

}
def download_all():
    for province, download_function in province_to_download_function.items():
        print(f"正在执行 {province} 的下载...")
        download_function()  # 调用下载函数
        #print(download_function.__name__)
        print(f"{province} 下载完成。")
        print( "\n", "==" * 20)


