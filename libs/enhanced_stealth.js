/*!
 * Enhanced Stealth Script for Media Crawler - 2024 Edition
 * 专门针对快手、抖音、B站等平台的反检测优化
 * Generated on: 2024-12-20
 * License: MIT
 */

(function() {
    'use strict';
    
    console.log('🚀 [Enhanced Stealth] 启动增强反检测脚本...');
    
    // =============================================
    // 1. 基础WebDriver特征隐藏
    // =============================================
    
    // 隐藏webdriver属性
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    
    // 删除webdriver相关变量
    delete window.webdriver;
    delete window.__webdriver_script_fn;
    delete window.__webdriver_evaluate;
    delete window.__selenium_evaluate;
    delete window.__webdriver_unwrapped;
    delete window.__fxdriver_evaluate;
    delete window.__driver_unwrapped;
    delete window.__webdriver_script_func;
    delete window.__webdriver_script_function;
    
    // =============================================
    // 2. Chrome特征完善
    // =============================================
    
    // 确保chrome对象完整
    if (!window.chrome) {
        window.chrome = {};
    }
    
    // 添加chrome.app
    if (!window.chrome.app) {
        window.chrome.app = {
            isInstalled: false,
            InstallState: {
                DISABLED: 'disabled',
                INSTALLED: 'installed',
                NOT_INSTALLED: 'not_installed'
            },
            RunningState: {
                CANNOT_RUN: 'cannot_run',
                READY_TO_RUN: 'ready_to_run',
                RUNNING: 'running'
            }
        };
    }
    
    // 添加chrome.runtime (快手检测重点)
    if (!window.chrome.runtime) {
        window.chrome.runtime = {
            onConnect: {
                addListener: function() {},
                removeListener: function() {},
                hasListener: function() { return false; }
            },
            onMessage: {
                addListener: function() {},
                removeListener: function() {},
                hasListener: function() { return false; }
            },
            onStartup: {
                addListener: function() {},
                removeListener: function() {},
                hasListener: function() { return false; }
            },
            connect: function() {
                throw new Error('Extension context invalidated.');
            },
            sendMessage: function() {
                throw new Error('Extension context invalidated.');
            }
        };
    }
    
    // =============================================
    // 3. 权限API完善 (抖音/B站检测)
    // =============================================
    
    if (!navigator.permissions) {
        navigator.permissions = {
            query: function(obj) {
                return Promise.resolve({
                    state: 'prompt',
                    onchange: null
                });
            }
        };
    }
    
    // =============================================
    // 4. 插件和扩展伪装
    // =============================================
    
    // 模拟真实的插件列表
    const mockPlugins = [
        {
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            version: '1'
        },
        {
            name: 'Chrome PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            description: '',
            version: '1'
        },
        {
            name: 'Native Client',
            filename: 'internal-nacl-plugin',
            description: '',
            version: '1'
        }
    ];
    
    Object.defineProperty(navigator, 'plugins', {
        get: function() {
            return mockPlugins;
        },
        configurable: true
    });
    
    // =============================================
    // 5. 语言和时区伪装
    // =============================================
    
    // 统一语言设置为中文
    Object.defineProperty(navigator, 'language', {
        get: function() { return 'zh-CN'; },
        configurable: true
    });
    
    Object.defineProperty(navigator, 'languages', {
        get: function() { return ['zh-CN', 'zh', 'en-US', 'en']; },
        configurable: true
    });
    
    // 时区设置
    if (Intl && Intl.DateTimeFormat) {
        const originalResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
        Intl.DateTimeFormat.prototype.resolvedOptions = function() {
            const options = originalResolvedOptions.call(this);
            options.timeZone = 'Asia/Shanghai';
            return options;
        };
    }
    
    // =============================================
    // 6. Canvas指纹防护
    // =============================================
    
    const getContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(contextType, ...args) {
        if (contextType === '2d') {
            const context = getContext.apply(this, arguments);
            if (context) {
                // 轻微扰动canvas指纹
                const originalFillText = context.fillText;
                context.fillText = function(text, x, y, maxWidth) {
                    // 添加微小的随机偏移
                    const offset = Math.random() * 0.1 - 0.05;
                    return originalFillText.call(this, text, x + offset, y + offset, maxWidth);
                };
            }
            return context;
        }
        return getContext.apply(this, arguments);
    };
    
    // =============================================
    // 7. WebGL指纹防护
    // =============================================
    
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // 模拟常见的GPU信息
        if (parameter === 37445) { // VENDOR
            return 'Google Inc. (Intel)';
        }
        if (parameter === 37446) { // RENDERER  
            return 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11-27.20.100.8681)';
        }
        return getParameter.call(this, parameter);
    };
    
    // =============================================
    // 8. 快手特殊检测对抗
    // =============================================
    
    // 快手可能检测的特殊属性
    window.external = window.external || {};
    window.external.AddSearchProvider = function() {};
    window.external.IsSearchProviderInstalled = function() { return 0; };
    
    // 模拟真实的屏幕属性
    Object.defineProperty(screen, 'availTop', {
        get: function() { return 0; },
        configurable: true
    });
    
    Object.defineProperty(screen, 'availLeft', {
        get: function() { return 0; },
        configurable: true
    });
    
    // =============================================
    // 9. 抖音/B站 特殊检测对抗
    // =============================================
    
    // 模拟真实的touch事件支持
    if (!('ontouchstart' in window)) {
        window.ontouchstart = null;
        window.ontouchmove = null;
        window.ontouchend = null;
        window.ontouchcancel = null;
    }
    
    // 电池API伪装
    if (!navigator.getBattery) {
        navigator.getBattery = function() {
            return Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 1,
                addEventListener: function() {},
                removeEventListener: function() {},
                dispatchEvent: function() { return true; }
            });
        };
    }
    
    // =============================================
    // 10. 内存和硬件信息伪装
    // =============================================
    
    // 内存信息
    if (!navigator.deviceMemory) {
        Object.defineProperty(navigator, 'deviceMemory', {
            get: function() { return 8; }, // 8GB内存
            configurable: true
        });
    }
    
    // CPU核心数
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: function() { return 8; }, // 8核CPU
        configurable: true
    });
    
    // =============================================
    // 11. 连接信息伪装
    // =============================================
    
    if (!navigator.connection) {
        Object.defineProperty(navigator, 'connection', {
            get: function() {
                return {
                    effectiveType: '4g',
                    rtt: 100,
                    downlink: 10,
                    saveData: false,
                    addEventListener: function() {},
                    removeEventListener: function() {}
                };
            },
            configurable: true
        });
    }
    
    // =============================================
    // 12. 媒体设备信息
    // =============================================
    
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
        navigator.mediaDevices.enumerateDevices = function() {
            return originalEnumerateDevices.call(this).then(devices => {
                // 确保返回一些基本设备信息
                if (devices.length === 0) {
                    return [
                        {
                            deviceId: 'default',
                            kind: 'audioinput',
                            label: '',
                            groupId: 'group1'
                        },
                        {
                            deviceId: 'default', 
                            kind: 'audiooutput',
                            label: '',
                            groupId: 'group2'
                        },
                        {
                            deviceId: 'default',
                            kind: 'videoinput', 
                            label: '',
                            groupId: 'group3'
                        }
                    ];
                }
                return devices;
            });
        };
    }
    
    // =============================================
    // 13. 隐藏自动化痕迹
    // =============================================
    
    // 清理可能暴露自动化的属性
    delete window.callPhantom;
    delete window._phantom;
    delete window.phantom;
    delete window.__phantomas;
    delete window.Buffer;
    delete window.emit;
    delete window.spawn;
    
    // 隐藏错误堆栈中的自动化信息
    const originalError = window.Error;
    window.Error = function(...args) {
        const error = new originalError(...args);
        if (error.stack) {
            error.stack = error.stack
                .replace(/\s+at\s+.*?(playwright|puppeteer|selenium).*?\n/gi, '')
                .replace(/\s+at\s+.*?webdriver.*?\n/gi, '');
        }
        return error;
    };
    
    // =============================================
    // 14. 快手专用反检测
    // =============================================
    
    // 快手可能检测的特殊对象
    window.ks = window.ks || {};
    
    // 模拟快手环境
    if (location.hostname.includes('kuaishou.com')) {
        // 添加快手可能期望的全局变量
        window.__INITIAL_STATE__ = window.__INITIAL_STATE__ || {};
        window.webpackJsonp = window.webpackJsonp || [];
        
        // 模拟快手的客户端检测
        Object.defineProperty(window, 'KS_CLIENT', {
            get: function() { return undefined; },
            configurable: true
        });
    }
    
    // =============================================
    // 15. 抖音专用反检测  
    // =============================================
    
    if (location.hostname.includes('douyin.com')) {
        // 抖音可能检测的属性
        window.byted_acrawler = window.byted_acrawler || {};
        window.__pace_options = window.__pace_options || {};
        
        // 模拟抖音环境变量
        window.SLARDAR_WEB_ID = '3715';
        window.LarkEnv = window.LarkEnv || {};
    }
    
    // =============================================
    // 16. B站专用反检测
    // =============================================
    
    if (location.hostname.includes('bilibili.com')) {
        // B站可能检测的属性
        window.__INITIAL_STATE__ = window.__INITIAL_STATE__ || {};
        window.reportObserver = window.reportObserver || {};
        
        // 模拟B站的buvid
        if (!localStorage.getItem('_uuid')) {
            localStorage.setItem('_uuid', 'B' + Date.now().toString(36) + Math.random().toString(36).substr(2));
        }
    }
    
    console.log('✅ [Enhanced Stealth] 增强反检测脚本加载完成');
    
})(); 