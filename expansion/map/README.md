# 96城地图 · v42

[地图预览](city-map-city-sea-preview-v42.html) · [完整图片](city-map-96-city-sea-v42.png) · [城池与道路数据](city-map-city-sea-plan-v42.json) · [城际海路](city-map-city-sea-links-v42.json) · [验证记录](city-map-city-sea-validation-v42.json)

本版使用96座城池和32×32城标，主图不显示城名。7条城际海路关系连接11座沿海城池，陆上接驳使用实线，海上使用虚线，共用段只画一次。地形与城池布局继承v41。

这是新游戏开发的地图设计稿，尚未写入原NES。地理位置、道路、港位及航迹具有游戏示意性质；来源与不确定性保留在海路JSON中。

`city-map-city-sea-plan-v42.json` 保存世界坐标，渲染视窗裁去左侧136像素；视窗为1352×1024。不要把屏幕横坐标直接写回世界坐标。

## 修改与重建

本目录包含v42海陆接驳的构建输入、v41地形和道路底稿、山体遮罩、渲染器及结果。v41以前的试制版本保留在原本地设计目录，未重复发布。

```sh
python3 -m pip install -r expansion/map/requirements.txt
npm --prefix expansion/map ci
python3 expansion/map/prepare-city-sea-v42.py
node expansion/map/render-city-sea-v42.cjs
python3 expansion/officers/build_report.py
```

渲染器默认使用本机Chrome；如未安装Chrome，可安装Playwright Chromium并把启动参数中的`channel: 'chrome'`去掉。重建会更新本目录的海路数据、预览和验证结果；v41输入保留，避免误改城池、河流和原有陆路。

PNG、HTML中的地形与城标为本工程设计和原游戏参考素材。原游戏及第三方素材的权利归各自权利人，仓库MIT许可证不改变这些权利。
