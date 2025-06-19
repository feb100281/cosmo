var dmcfuncs = window.dashMantineFunctions = window.dashMantineFunctions || {};

// Базовая функция (работает)
dmcfuncs.formatNumberIntl = (value) => {
  return '₽' + (value / 1000000).toFixed(1) + ' млн';
};

window.dashMantineFunctions.formatRubles = (value) => {
  return '₽' + (value / 1000000).toFixed(1) + ' млн';
};

// assets/format-numbers.js
dmcfuncs.formatRublesMillions = function(value) {
  console.log("Получено значение:", value);  // Дебаг в консоль
  if (value == null || isNaN(value)) return "₽0 млн";
  return "₽" + (value / 1_000_000).toFixed(1).replace(".", ",") + " млн";
};
// Дебаг-проверка: выводим в консоль, что функция зарегистрирована
console.log("Функция formatRublesMillions загружена:", dmcfuncs.formatRublesMillions);

