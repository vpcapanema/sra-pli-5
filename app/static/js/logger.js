/* ==========================================================================
   SRA - Sistema de Logging Centralizado

   Sistema de logging para registrar atividades no console do navegador.
   Registra eventos de navegação, cliques, formulários, erros e atividades
   específicas de cada página.

   Uso:
   - Logger.info('mensagem', dados)
   - Logger.warn('mensagem', dados)
   - Logger.error('mensagem', dados)
   - Logger.debug('mensagem', dados)
   - Logger.pageView(nomePagina)
   - Logger.click(elemento, contexto)
   - Logger.formSubmit(formulario, dados)
   ========================================================================== */

(function () {
    'use strict';

    var Logger = {
        // Configurações
        enabled: true,
        prefix: '[SRA]',
        logLevel: 'debug', // debug, info, warn, error

        // Cores para console
        colors: {
            info: '#2196F3',
            warn: '#FF9800',
            error: '#F44336',
            debug: '#9E9E9E',
            page: '#4CAF50',
            click: '#9C27B0',
            form: '#00BCD4'
        },

        // Obter nome da página atual
        getPageName: function () {
            var path = window.location.pathname;
            var page = path.split('/').pop() || 'index';
            if (page.indexOf('.') !== -1) {
                page = page.split('.')[0];
            }
            return page;
        },

        // Obter timestamp formatado
        getTimestamp: function () {
            var now = new Date();
            return now.toISOString().split('T')[1].split('.')[0];
        },

        // Formatar mensagem com estilo
        formatMessage: function (level, message, data) {
            var timestamp = this.getTimestamp();
            var page = this.getPageName();
            var prefix = this.prefix + ' [' + timestamp + '] [' + page + ']';
            
            if (data) {
                return prefix + ' ' + message + ' %O';
            }
            return prefix + ' ' + message;
        },

        // Log genérico
        log: function (level, message, data) {
            if (!this.enabled) return;
            
            var levels = { debug: 0, info: 1, warn: 2, error: 3 };
            if (levels[level] < levels[this.logLevel]) return;

            var style = 'color: ' + this.colors[level] + '; font-weight: bold;';
            var formattedMsg = this.formatMessage(level, message, data);

            switch (level) {
                case 'error':
                    console.error('%c' + formattedMsg, style, data || '');
                    break;
                case 'warn':
                    console.warn('%c' + formattedMsg, style, data || '');
                    break;
                case 'info':
                    console.info('%c' + formattedMsg, style, data || '');
                    break;
                case 'debug':
                default:
                    console.log('%c' + formattedMsg, style, data || '');
                    break;
            }
        },

        // Métodos de conveniência
        info: function (message, data) {
            this.log('info', message, data);
        },

        warn: function (message, data) {
            this.log('warn', message, data);
        },

        error: function (message, data) {
            this.log('error', message, data);
        },

        debug: function (message, data) {
            this.log('debug', message, data);
        },

        // Log de visualização de página
        pageView: function (pageName) {
            var name = pageName || this.getPageName();
            var style = 'color: ' + this.colors.page + '; font-weight: bold; font-size: 14px;';
            var timestamp = this.getTimestamp();
            console.log(
                '%c' + this.prefix + ' [' + timestamp + '] === PÁGINA CARREGADA: ' + name + ' ===',
                style
            );
            this.info('URL: ' + window.location.href);
            this.info('Referer: ' + (document.referrer || 'N/A'));
        },

        // Log de clique
        click: function (element, context) {
            if (!element) return;
            
            var tagName = element.tagName.toLowerCase();
            var id = element.id ? '#' + element.id : '';
            var classes = element.className ? '.' + element.className.split(' ').join('.') : '';
            var selector = tagName + id + classes;
            var text = element.textContent ? element.textContent.trim().substring(0, 30) : '';
            
            var data = {
                selector: selector,
                text: text,
                context: context || 'unknown'
            };
            
            var style = 'color: ' + this.colors.click + '; font-weight: bold;';
            var timestamp = this.getTimestamp();
            console.log(
                '%c' + this.prefix + ' [' + timestamp + '] 🖱️ CLIQUE: ' + selector,
                style,
                data
            );
        },

        // Log de submissão de formulário
        formSubmit: function (form, data) {
            if (!form) return;
            
            var action = form.action || 'unknown';
            var method = form.method || 'unknown';
            var formData = {};
            
            if (data) {
                formData = data;
            } else {
                // Coletar dados do formulário
                var inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(function (input) {
                    if (input.name) {
                        formData[input.name] = input.type === 'password' ? '***' : input.value;
                    }
                });
            }
            
            var logData = {
                action: action,
                method: method,
                data: formData
            };
            
            var style = 'color: ' + this.colors.form + '; font-weight: bold;';
            var timestamp = this.getTimestamp();
            console.log(
                '%c' + this.prefix + ' [' + timestamp + '] 📝 FORMULÁRIO SUBMETIDO: ' + method.toUpperCase() + ' ' + action,
                style,
                logData
            );
        },

        // Log de erro
        logError: function (error, context) {
            var data = {
                message: error.message,
                stack: error.stack,
                context: context || 'unknown'
            };
            this.error('ERRO: ' + error.message, data);
        },

        // Log de requisição HTTP
        httpRequest: function (method, url, data) {
            this.info('🌐 HTTP ' + method.toUpperCase() + ': ' + url, data);
        },

        // Log de resposta HTTP
        httpResponse: function (method, url, status, data) {
            var style = status >= 400 ? 'color: ' + this.colors.error : 'color: ' + this.colors.info;
            var timestamp = this.getTimestamp();
            console.log(
                '%c' + this.prefix + ' [' + timestamp + '] 📥 RESPOSTA HTTP: ' + status + ' ' + method.toUpperCase() + ' ' + url,
                style,
                data
            );
        },

        // Inicializar logging automático de eventos globais
        initAutoLogging: function () {
            var self = this;

            // Log de cliques em elementos com data-log-click
            document.addEventListener('click', function (e) {
                var target = e.target.closest('[data-log-click]');
                if (target) {
                    var context = target.dataset.logClick || 'click';
                    self.click(target, context);
                }
            }, true);

            // Log de submissão de formulários
            document.addEventListener('submit', function (e) {
                var form = e.target;
                if (form.tagName === 'FORM') {
                    self.formSubmit(form);
                }
            }, true);

            // Log de erros globais
            window.addEventListener('error', function (e) {
                self.logError(e.error, 'global');
            });

            // Log de erros de promises não tratadas
            window.addEventListener('unhandledrejection', function (e) {
                self.error('Promise rejeitada não tratada', {
                    reason: e.reason,
                    promise: e.promise
                });
            });

            // Log de navegação (History API)
            var originalPushState = history.pushState;
            var originalReplaceState = history.replaceState;

            history.pushState = function () {
                originalPushState.apply(this, arguments);
                self.info('Navegação (pushState): ' + arguments[2]);
            };

            history.replaceState = function () {
                originalReplaceState.apply(this, arguments);
                self.info('Navegação (replaceState): ' + arguments[2]);
            };

            window.addEventListener('popstate', function () {
                self.info('Navegação (popstate): ' + window.location.pathname);
            });
        }
    };

    // Expor Logger globalmente
    window.SRALogger = Logger;

    // Inicializar automaticamente
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            Logger.initAutoLogging();
            Logger.pageView();
        });
    } else {
        Logger.initAutoLogging();
        Logger.pageView();
    }

})();
