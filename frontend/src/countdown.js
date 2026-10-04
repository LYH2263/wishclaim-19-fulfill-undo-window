// 倒计时/撤销窗共用格式化 —— 详情、我的认领、已完成同钉
export function fmtRemaining(s) {
  if (s == null) return '—'
  if (s <= 0) return '已到期'
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  return (h ? h + '时' : '') + (h || m ? m + '分' : '') + sec + '秒'
}
