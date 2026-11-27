# 数据字典

- actual_received 是对应运输队在目标处的真实入库。final_destination 标记其是否计入计划最终经济实收。
- 多个中间批次可对同一笔粮形成多张作业收据。transport_handling 加总全部运输作业，final_grain 仅加总真正终点。
- actual_stock 才是实际官仓，tagged_stock 是其中已标记用途的份额。tagged_utilization 除以原物理仓容。
- original_deadline 与 promise 使用回合数。日序采用凭证落账旬开始时的战役日。额度空值表示本实验没有适用记录。
- 额度选择的世界仅用于受控试验。physical-controls 的纯海样本保留地图配置模板及实际装载口粮，不能用作自然观战海运实收。
- 路线报告的 work 是引擎固定点工作量，1 天等于 DAY_TICKS。接岸审计的计数按剧本及允许方向累加。
- process_peak_rss 是进程高水位。短样本 CPU 行不作为正式回合性能门槛。
