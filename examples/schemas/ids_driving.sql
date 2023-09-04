CREATE TABLE ids_driving (
  org_id bigint comment '集团id',
  motor_id bigint comment '车队id',
  route_id bigint comment '线路id',
  emp_id bigint comment '司机id',
  bus_self_no text comment '车辆编码',
  plan_seq_num text comment '计划班次数',
  real_start_time timestamp comment '实际发车时间',
  dispatch_start_time timestamp comment '调度开始时间',
  fst_send_time timestamp comment '首班发车时间',
  plan_mile double precision comment '计划里程',
  gps_mile double precision comment 'gps 里程',
  operate_state int,
  is_loop int comment '是否环形',
  exec_date date comment '营运日期'
);