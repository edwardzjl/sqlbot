CREATE TABLE trade_segment_by_min10_width (
  route_id int comment '线路ID',
  route_name text comment '线路名称',
  main int comment '所属主线ID，如果本身是主线路则为空',
  direction int comment '线段方向：4上行，5下行',
  plan_id text comment '方案ID',
  group_of_route int cmment '线路所属集团',
  subsidiary int comment '线路所属子公司',
  weather_type int comment '天气类型，0=非雨雪天气|1=雨天|2=雪天',
  trade_date date comment '运营日期',
  day_of_week int comment '星期几, 1~7',
  merchant_id int comment '线路所属集团商户编码',
  city_code text comment '线路城市编码',
  biz_distance_sum int comment '运营里程，单位KM',
  biz_time_sum int comment '运营时长，单位分钟',
  displan_sum int comment '班次数'
);