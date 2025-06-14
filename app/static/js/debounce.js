/**
 * 防抖动工具函数
 * 防止按钮在短时间内被多次点击，导致重复提交
 */

/**
 * 防抖函数 - 确保函数在一段时间内只执行一次
 * @param {Function} func 需要执行的函数
 * @param {number} wait 等待时间（毫秒）
 * @param {boolean} immediate 是否立即执行
 * @returns {Function} 经过防抖处理的函数
 */
function debounce(func, wait = 300, immediate = false) {
  let timeout;
  
  return function executedFunction(...args) {
    const context = this;
    
    // 清除之前的定时器
    const later = function() {
      timeout = null;
      if (!immediate) func.apply(context, args);
    };
    
    const callNow = immediate && !timeout;
    
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    
    if (callNow) func.apply(context, args);
  };
}

/**
 * 初始化带有防抖功能的按钮
 * 为所有带有data-debounce属性的按钮添加防抖功能
 * @param {number} delay 防抖延迟时间（毫秒），默认1000ms
 */
function initDebouncedButtons(delay = 1000) {
  // 获取所有带有data-debounce属性的按钮
  const buttons = document.querySelectorAll('[data-debounce]');
  
  buttons.forEach(button => {
    // 获取按钮原始的点击事件处理函数
    const originalClick = button.onclick;
    
    if (originalClick) {
      // 使用防抖函数包装原始的点击事件处理函数
      button.onclick = debounce(function(event) {
        // 添加禁用状态
        button.disabled = true;
        button.classList.add('btn-disabled');
        
        // 保存原始文本
        const originalText = button.textContent || button.innerText;
        
        // 如果按钮有data-loading-text属性，则显示加载文本
        if (button.dataset.loadingText) {
          button.textContent = button.dataset.loadingText;
        }
        
        // 执行原始点击事件
        originalClick.call(this, event);
        
        // 延迟后恢复按钮状态
        setTimeout(() => {
          button.disabled = false;
          button.classList.remove('btn-disabled');
          button.textContent = originalText;
        }, delay);
      }, delay, true);
    }
  });
}

/**
 * 为单个按钮添加防抖功能
 * @param {HTMLElement} button 按钮元素
 * @param {Function} clickHandler 点击处理函数
 * @param {number} delay 防抖延迟时间（毫秒），默认1000ms
 * @param {string} loadingText 加载中显示的文本，可选
 */
function addButtonDebounce(button, clickHandler, delay = 1000, loadingText = null) {
  if (!button) return;
  
  button.addEventListener('click', debounce(function(event) {
    // 添加禁用状态
    button.disabled = true;
    button.classList.add('btn-disabled');
    
    // 保存原始文本
    const originalText = button.textContent || button.innerText;
    
    // 如果提供了加载文本，则显示
    if (loadingText) {
      button.textContent = loadingText;
    }
    
    // 执行点击处理函数
    if (typeof clickHandler === 'function') {
      clickHandler.call(this, event);
    }
    
    // 延迟后恢复按钮状态
    setTimeout(() => {
      button.disabled = false;
      button.classList.remove('btn-disabled');
      button.textContent = originalText;
    }, delay);
  }, delay, true));
}

// 页面加载完成后自动初始化所有防抖按钮
document.addEventListener('DOMContentLoaded', function() {
  initDebouncedButtons();
}); 