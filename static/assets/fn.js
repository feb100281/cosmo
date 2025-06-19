var dmcfuncs = window.dashMantineFunctions = window.dashMantineFunctions || {};

dmcfuncs.fn = (value) => {
  return new Intl.NumberFormat('en-US').format(value);
};
