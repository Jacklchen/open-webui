<script>
    // 保持原有脚本部分不变
    import { toast } from 'svelte-sonner';
    import { onMount, getContext, tick } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/stores';
    import { getBackendConfig } from '$lib/apis';
    import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';
    import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
    import { WEBUI_NAME, config, user, socket } from '$lib/stores';
    import { generateInitialsImage, canvasPixelTest } from '$lib/utils';
    import Spinner from '$lib/components/common/Spinner.svelte';
    import OnBoarding from '$lib/components/OnBoarding.svelte';
    const i18n = getContext('i18n');
    
    // Authentication logic
    let loaded = false;
    let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';
    let name = '';
    let email = '';
    let password = '';
    let ldapUsername = '';
    
    // Dynamic time
    let currentTime = new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
    });
    let currentDate = new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
    });
    let timeInterval;
    
    // 添加新的状态变量
    let showPassword = false;
    let emailValid = false;
    
    function updateTime() {
        currentTime = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
        });
        currentDate = new Date().toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
        });
    }
    
    // Authentication functions remain unchanged
    const querystringValue = (key) => {
        const querystring = window.location.search;
        const urlParams = new URLSearchParams(querystring);
        return urlParams.get(key);
    };
    
    const setSessionUser = async (sessionUser) => {
        if (sessionUser) {
            console.log(sessionUser);
            toast.success($i18n.t(`You're now logged in.`));
            if (sessionUser.token) {
                localStorage.token = sessionUser.token;
            }
            $socket.emit('user-join', { auth: { token: sessionUser.token } });
            await user.set(sessionUser);
            await config.set(await getBackendConfig());
            const redirectPath = querystringValue('redirect') || '/';
            goto(redirectPath);
        }
    };
    
    const signInHandler = async () => {
        const sessionUser = await userSignIn(email, password).catch((error) => {
            toast.error(`${error}`);
            return null;
        });
        await setSessionUser(sessionUser);
    };
    
    const signUpHandler = async () => {
        const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
            (error) => {
                toast.error(`${error}`);
                return null;
            }
        );
        await setSessionUser(sessionUser);
    };
    
    const ldapSignInHandler = async () => {
        const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
            toast.error(`${error}`);
            return null;
        });
        await setSessionUser(sessionUser);
    };
    
    // 添加邮箱验证函数
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
    
    // 处理邮箱输入
    function handleEmailInput() {
        emailValid = validateEmail(email);
        if (emailValid) {
            showPassword = true;
        }
    }
    
    // 修改提交处理函数
    const submitHandler = async () => {
        if (!emailValid) {
            return;
        }
        
        // Show loading state
        const loadingButton = document.getElementById('submit-button');
        if (loadingButton) {
            loadingButton.disabled = true;
            loadingButton.classList.add('loading');
        }
        
        try {
            if (mode === 'ldap') {
                await ldapSignInHandler();
            } else if (mode === 'signin') {
                await signInHandler();
            } else {
                await signUpHandler();
            }
        } finally {
            // Reset button state
            if (loadingButton) {
                loadingButton.disabled = false;
                loadingButton.classList.remove('loading');
            }
        }
    };
    
    const checkOauthCallback = async () => {
        if (!$page.url.hash) return;
        const hash = $page.url.hash.substring(1);
        if (!hash) return;
        const params = new URLSearchParams(hash);
        const token = params.get('token');
        if (!token) return;
        const sessionUser = await getSessionUser(token).catch((error) => {
            toast.error(`${error}`);
            return null;
        });
        if (!sessionUser) return;
        localStorage.token = token;
        await setSessionUser(sessionUser);
    };
    
    let onboarding = false;
    
    async function setLogoImage() {
        await tick();
        const logo = document.getElementById('logo');
        if (logo) {
            const isDarkMode = document.documentElement.classList.contains('dark');
            if (isDarkMode) {
                const darkImage = new Image();
                darkImage.src = '/favicon.png';
                darkImage.onload = () => {
                    logo.src = '/favicon.png';
                    logo.style.filter = '';
                };
                darkImage.onerror = () => {
                    logo.style.filter = 'invert(1)';
                };
            } else {
                logo.src = '/favicon.png';
            }
        }
    }
    
    onMount(async () => {
        if ($user !== undefined) {
            await goto('/');
        }
        
        // Start dynamic time updates
        timeInterval = setInterval(updateTime, 1000);
        updateTime();
        
        await checkOauthCallback();
        loaded = true;
        setLogoImage();
        
        if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
            await signInHandler();
        } else {
            onboarding = $config?.onboarding ?? false;
        }
        
        return () => {
            clearInterval(timeInterval);
        };
    });
</script>

<svelte:head>
    <title>{`${$WEBUI_NAME}`}</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</svelte:head>

<OnBoarding
    bind:show={onboarding}
    getStartedHandler={() => {
        onboarding = false;
        mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
    }}
/>

<div class="login-page">
    <!-- 背景动效 -->
    <div class="animated-background">
        <div class="gradient-sphere sphere-1"></div>
        <div class="gradient-sphere sphere-2"></div>
        <div class="gradient-sphere sphere-3"></div>
        <div class="grid-overlay"></div>
        
        <!-- 大型背景文字 -->
        <div class="background-text">XUB AI</div>
    </div>
    
    <!-- Logo in top left -->
    <div class="top-logo">
        <img id="logo" crossorigin="anonymous" src="{WEBUI_BASE_URL}/static/splash.png" alt="logo" />
        <h1>XUB AI</h1>
    </div>
    
    <!-- 时间显示 -->
    <div class="time-display">
        <div class="time">{currentTime}</div>
        <div class="date">{currentDate}</div>
    </div>
    
    <!-- 窗口顶部拖动区域 -->
    <div class="w-full absolute top-0 left-0 right-0 h-8 drag-region"></div>
    
    {#if loaded}
    <div class="login-container">        
        <!-- 登录卡片 -->
        <div class="card">
            <div class="card-header">
                <h2>{mode === 'ldap' ? $i18n.t('LDAP Authentication') : (mode === 'signin' ? $i18n.t('Welcome Back') : $i18n.t('Create Account'))}</h2>
                <p class="subtitle">{mode === 'ldap' ? $i18n.t('Enter your credentials to continue') : (mode === 'signin' ? $i18n.t('Sign in to your account') : $i18n.t('Join our intelligent platform'))}</p>
            </div>
            
            {#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
                <div class="signing-in">
                    <div>{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}</div>
                    <div><Spinner /></div>
                </div>
            {:else}
                <form on:submit|preventDefault={submitHandler}>
                    {#if mode === 'signup'}
                        <div class="form-group">
                            <label for="name">{$i18n.t('Name')}</label>
                            <div class="input-wrapper">
                                <svg class="input-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                                <input
                                    id="name"
                                    bind:value={name}
                                    type="text"
                                    autocomplete="name"
                                    placeholder={$i18n.t('Enter your full name')}
                                    required
                                />
                            </div>
                        </div>
                    {/if}
                    
                    {#if mode === 'ldap'}
                        <div class="form-group">
                            <label for="username">{$i18n.t('Username')}</label>
                            <div class="input-wrapper">
                                <svg class="input-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                                <input
                                    id="username"
                                    bind:value={ldapUsername}
                                    type="text"
                                    autocomplete="username"
                                    name="username"
                                    placeholder={$i18n.t('Enter your username')}
                                    required
                                />
                            </div>
                        </div>
                    {:else}
                        <div class="form-group">
                            <label for="email">{$i18n.t('Email')}</label>
                            <div class="input-wrapper">
                                <svg class="input-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
                                <input
                                    id="email"
                                    bind:value={email}
                                    on:input={handleEmailInput}
                                    type="email"
                                    autocomplete="email"
                                    name="email"
                                    placeholder={$i18n.t('Enter your email')}
                                    required
                                />
                            </div>
                            {#if email && !emailValid}
                                <div class="error-message">{$i18n.t('Please enter a valid email address')}</div>
                            {/if}
                        </div>
                    {/if}
                    
                    {#if showPassword || mode === 'ldap'}
                        <div class="form-group password-group" class:slide-in={showPassword}>
                            <label for="password">{$i18n.t('Password')}</label>
                            <div class="input-wrapper">
                                <svg class="input-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                                <input
                                    id="password"
                                    bind:value={password}
                                    type="password"
                                    placeholder={$i18n.t('Enter your password')}
                                    autocomplete="current-password"
                                    name="current-password"
                                    required
                                />
                            </div>
                        </div>
                    {/if}
                    
                    {#if $config?.features.enable_login_form || $config?.features.enable_ldap}
                        <button
                            id="submit-button"
                            class="submit-button"
                            type="submit"
                        >
                            {#if !showPassword && !mode === 'ldap'}
                                {$i18n.t('Next')}
                            {:else}
                                {mode === 'ldap' 
                                    ? $i18n.t('Authenticate')
                                    : (mode === 'signin' ? $i18n.t('Sign In') : $i18n.t('Create Account'))}
                            {/if}
                            <span class="btn-indicator"></span>
                        </button>
                        
                        {#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
                            <div class="toggle-mode">
                                {mode === 'signin'
                                    ? $i18n.t("Don't have an account?")
                                    : $i18n.t('Already have an account?')}
                                <button
                                    type="button"
                                    on:click={() => {
                                        mode = mode === 'signin' ? 'signup' : 'signin';
                                        showPassword = false;
                                    }}
                                >
                                    {mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
                                </button>
                            </div>
                        {/if}
                    {/if}
                </form>
                
                <!-- OAuth providers -->
                {#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
                    <div class="oauth-divider">
                        {#if $config?.features.enable_login_form || $config?.features.enable_ldap}
                            <span>{$i18n.t('or')}</span>
                        {/if}
                    </div>
                    
                    <div class="oauth-container">
                        {#if $config?.oauth?.providers?.google}
                            <button
                                class="oauth-button google"
                                on:click={() => {
                                    window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
                                }}
                            >
                                <svg viewBox="0 0 24 24" width="20" height="20">
                                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                                </svg>
                            </button>
                        {/if}
                        
                        {#if $config?.oauth?.providers?.github}
                            <button
                                class="oauth-button github"
                                on:click={() => {
                                    window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
                                }}
                            >
                                <svg viewBox="0 0 24 24" width="20" height="20">
                                    <path fill="currentColor" d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
                                </svg>
                            </button>
                        {/if}
                        
                        {#if $config?.oauth?.providers?.microsoft}
                            <button
                                class="oauth-button microsoft"
                                on:click={() => {
                                    window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
                                }}
                            >
                                <svg viewBox="0 0 24 24" width="20" height="20">
                                    <path fill="#f25022" d="M0 0h11.5v11.5H0z"/>
                                    <path fill="#00a4ef" d="M0 12.5h11.5V24H0z"/>
                                    <path fill="#7fba00" d="M12.5 0H24v11.5H12.5z"/>
                                    <path fill="#ffb900" d="M12.5 12.5H24V24H12.5z"/>
                                </svg>
                            </button>
                        {/if}
                        
                        {#if $config?.oauth?.providers?.oidc}
                            <button
                                class="oauth-button oidc"
                                on:click={() => {
                                    window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
                                }}
                            >
                                <svg viewBox="0 0 24 24" width="20" height="20">
                                    <path fill="currentColor" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/>
                                </svg>
                            </button>
                        {/if}
                    </div>
                {/if}
                
                <!-- Telegram Community Link -->
                <div class="telegram-community">
                    <a href="https://t.me/madoukas" target="_blank" rel="noopener noreferrer" class="telegram-link">
                        <svg viewBox="0 0 24 24" width="20" height="20">
                            <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.11.02-1.93 1.23-5.46 3.62-.52.36-.99.53-1.41.52-.46-.01-1.35-.26-2.01-.48-.81-.27-1.45-.42-1.4-.89.03-.24.37-.49 1.02-.75 4.02-1.75 6.69-2.9 8.03-3.46 3.85-1.6 4.64-1.88 5.17-1.89.11 0 .37.03.54.17.14.12.18.28.2.45-.02.14-.02.3-.03.42z"/>
                        </svg>
                        <span>Join our Telegram Community</span>
                    </a>
                </div>
                
                {#if $config?.features.enable_ldap && $config?.features.enable_login_form}
                    <div class="switch-auth-mode">
                        <button
                            type="button"
                            on:click={() => {
                                mode = mode === 'ldap'
                                    ? ($config?.onboarding ?? false) ? 'signup' : 'signin'
                                    : 'ldap';
                            }}
                        >
                            {mode === 'ldap'
                                ? $i18n.t('Continue with Email')
                                : $i18n.t('Continue with LDAP')}
                        </button>
                    </div>
                {/if}
            {/if}
        </div>
    </div>
    {/if}
</div>

<style>
    :root {
        --brand-primary: #6366f1;
        --brand-secondary: #4f46e5;
        --brand-accent: #818cf8;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --bg-primary: #ffffff;
        --bg-secondary: #f8fafc;
        --border-color: #e2e8f0;
        --input-bg: #f8fafc;
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
    }
    
    @media (prefers-color-scheme: dark) {
        :root {
            --brand-primary: #818cf8;
            --brand-secondary: #6366f1;
            --brand-accent: #4f46e5;
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --border-color: #334155;
            --input-bg: #1e293b;
            --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.3);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.3);
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        }
    }
    
    /* Global styles */
    :global(body) {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: var(--bg-primary);
        color: var(--text-primary);
        margin: 0;
        padding: 0;
        min-height: 100vh;
        overflow: hidden;
    }
    
    /* Login page */
    .login-page {
        position: relative;
        min-height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
        overflow: hidden;
    }
    
    /* Animated background */
    .animated-background {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        overflow: hidden;
        z-index: -1;
    }
    
    .grid-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image: 
            linear-gradient(to right, rgba(99, 102, 241, 0.03) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(99, 102, 241, 0.03) 1px, transparent 1px);
        background-size: 40px 40px;
        background-position: 0 0;
        z-index: 1;
    }
    
    /* Background text */
    .background-text {
        position: absolute;
        font-size: 25vw;
        font-weight: 900;
        color: rgba(99, 102, 241, 0.03);
        pointer-events: none;
        white-space: nowrap;
        line-height: 1;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-5deg);
        z-index: 0;
        letter-spacing: -0.05em;
        user-select: none;
    }
    
    @media (prefers-color-scheme: dark) {
        .background-text {
            color: rgba(99, 102, 241, 0.035);
        }
    }
    
    .gradient-sphere {
        position: absolute;
        border-radius: 50%;
        filter: blur(60px);
        opacity: 0.4;
        animation: float 20s infinite ease-in-out;
    }
    
    .sphere-1 {
        width: 30vw;
        height: 30vw;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.7) 0%, rgba(99, 102, 241, 0) 70%);
        top: -10vh;
        right: -5vw;
        animation-delay: 0s;
    }
    
    .sphere-2 {
        width: 45vw;
        height: 45vw;
        background: radial-gradient(circle, rgba(79, 70, 229, 0.7) 0%, rgba(79, 70, 229, 0) 70%);
        bottom: -15vh;
        left: -10vw;
        animation-delay: -5s;
    }
    
    .sphere-3 {
        width: 20vw;
        height: 20vw;
        background: radial-gradient(circle, rgba(129, 140, 248, 0.7) 0%, rgba(129, 140, 248, 0) 70%);
        top: 40vh;
        right: 20vw;
        animation-delay: -10s;
    }
    
    @keyframes float {
        0%, 100% {
            transform: translate(0, 0);
        }
        25% {
            transform: translate(5%, 5%);
        }
        50% {
            transform: translate(0, 10%);
        }
        75% {
            transform: translate(-5%, 5%);
        }
    }
    
    /* Top logo */
    .top-logo {
        position: absolute;
        top: 32px;
        left: 32px;
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 10;
    }
    
    .top-logo img {
        width: 42px;
        height: 42px;
        border-radius: 10px;
        box-shadow: var(--shadow-sm);
    }
    
    .top-logo h1 {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
    
    /* Time display */
    .time-display {
        position: absolute;
        top: 32px;
        right: 32px;
        background: var(--bg-primary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 10px 16px;
        box-shadow: var(--shadow-sm);
        text-align: right;
        line-height: 1.2;
        z-index: 10;
    }
    
    .time {
        font-size: 1.25rem;
        font-weight: 500;
        color: var(--brand-primary);
    }
    
    .date {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-top: 4px;
    }
    
    /* Login container */
    .login-container {
        width: 100%;
        max-width: 550px;
        margin: 0 auto;
        padding: 2.5rem;
        position: relative;
        z-index: 2;
        box-sizing: border-box;
        animation: fadeIn 0.6s ease-out;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Card */
    .card {
        background: var(--bg-primary);
        border-radius: 20px;
        padding: 2.5rem;
        box-shadow: var(--shadow-xl);
        border: 1px solid var(--border-color);
        animation: slideUp 0.5s ease-out;
        position: relative;
        overflow: hidden;
    }
    
    .card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 5px;
        background: linear-gradient(90deg, var(--brand-primary), var(--brand-secondary), var(--brand-accent));
        z-index: 1;
    }
    
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .card-header {
        margin-bottom: 1.5rem;
    }
    
    .card-header h2 {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0 0 0.75rem;
        color: var(--text-primary);
    }
    
    .subtitle {
        font-size: 1rem;
        color: var(--text-secondary);
        margin: 0;
    }
    
    /* Form styling */
    .form-group {
        margin-bottom: 1.25rem;
    }
    
    .form-group label {
        display: block;
        font-size: 1rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
        color: var(--text-primary);
    }
    
    .input-wrapper {
        position: relative;
        display: flex;
        align-items: center;
    }
    
    .input-icon {
        position: absolute;
        left: 1rem;
        color: var(--text-secondary);
    }
    
    .input-wrapper input {
        width: 100%;
        padding: 0.875rem 1rem 0.875rem 2.75rem;
        font-size: 1rem;
        border: 1px solid var(--border-color);
        border-radius: 12px;
        background-color: var(--input-bg);
        color: var(--text-primary);
        transition: all 0.3s ease;
        font-family: inherit;
    }
    
    .input-wrapper input:focus {
        outline: none;
        border-color: var(--brand-primary);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
    }
    
    .input-wrapper input::placeholder {
        color: var(--text-secondary);
        opacity: 0.6;
    }
    
    /* Submit button */
    .submit-button {
        width: 100%;
        padding: 1rem;
        background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
        color: white;
        border: none;
        border-radius: 12px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: var(--shadow-md);
        font-family: inherit;
    }
    
    .submit-button:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow-lg);
    }
    
    .submit-button:active {
        transform: translateY(1px);
    }
    
    .btn-indicator {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transform: translateX(-100%);
    }
    
    .submit-button:hover .btn-indicator {
        animation: btn-shine 1.5s infinite;
    }
    
    @keyframes btn-shine {
        100% {
            transform: translateX(100%);
        }
    }
    
    .submit-button.loading {
        opacity: 0.8;
        pointer-events: none;
    }
    
    .submit-button.loading::after {
        content: "";
        position: absolute;
        top: 50%;
        right: 1.5rem;
        transform: translateY(-50%);
        width: 1rem;
        height: 1rem;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-top-color: white;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
        to {
            transform: translateY(-50%) rotate(360deg);
        }
    }
    
    /* Toggle mode */
    .toggle-mode {
        text-align: center;
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-bottom: 1.25rem;
    }
    
    .toggle-mode button {
        background: none;
        border: none;
        color: var(--brand-primary);
        font-weight: 600;
        cursor: pointer;
        padding: 0;
        font-size: 0.875rem;
        margin-left: 0.25rem;
        font-family: inherit;
        transition: color 0.2s;
    }
    
    .toggle-mode button:hover {
        color: var(--brand-secondary);
        text-decoration: underline;
    }
    
    /* OAuth section */
    .oauth-divider {
        display: flex;
        align-items: center;
        margin: 1rem 0;
        color: var(--text-secondary);
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .oauth-divider::before, 
    .oauth-divider::after {
        content: "";
        flex: 1;
        height: 1px;
        background: linear-gradient(to right, transparent, var(--border-color), transparent);
    }
    
    .oauth-divider::before {
        margin-right: 0.5rem;
    }
    
    .oauth-divider::after {
        margin-left: 0.5rem;
    }
    
    .oauth-divider span {
        padding: 0 0.5rem;
        color: var(--text-secondary);
        font-weight: 500;
    }
    
    .oauth-container {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    
    .oauth-button {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 56px;
        height: 56px;
        border-radius: 12px;
        border: 1px solid var(--border-color);
        background-color: var(--bg-primary);
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: var(--shadow-sm);
        position: relative;
        overflow: hidden;
    }
    
    .oauth-button.google {
        background-color: #4285F4;
    }
    
    .oauth-button.google:hover {
        background-color: #357ABD;
    }
    
    .oauth-button.google svg {
        width: 24px;
        height: 24px;
        color: white;
    }
    
    .oauth-button.github {
        background-color: white;
        border-color: #dadce0;
    }
    
    .oauth-button.github:hover {
        background-color: #f8f9fa;
        border-color: #dadce0;
    }
    
    .oauth-button.github svg {
        width: 24px;
        height: 24px;
        color: #24292e;
    }
    
    .oauth-button.microsoft {
        background-color: #2F2F2F;
    }
    
    .oauth-button.microsoft:hover {
        background-color: #1f1f1f;
    }
    
    .oauth-button.microsoft svg {
        width: 24px;
        height: 24px;
        color: white;
    }
    
    .oauth-button.oidc {
        background-color: var(--brand-primary);
    }
    
    .oauth-button.oidc:hover {
        background-color: var(--brand-secondary);
    }
    
    .oauth-button.oidc svg {
        width: 24px;
        height: 24px;
        color: white;
    }
    
    /* Switch auth mode */
    .switch-auth-mode {
        text-align: center;
        margin-top: 0.5rem;
    }
    
    .switch-auth-mode button {
        background: none;
        border: none;
        color: var(--brand-primary);
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: color 0.2s;
        padding: 0;
        font-family: inherit;
    }
    
    .switch-auth-mode button:hover {
        color: var(--brand-secondary);
        text-decoration: underline;
    }
    
    /* Signing in state */
    .signing-in {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.75rem;
        color: var(--text-secondary);
        padding: 2rem 0;
    }
    
    /* Telegram Community Link */
    .telegram-community {
        margin-top: 1rem;
        text-align: center;
    }
    
    .telegram-link {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.375rem 0.75rem;
        background: linear-gradient(135deg, #0088cc, #00a2ff);
        color: white;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.75rem;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-sm);
    }
    
    .telegram-link:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow-md);
    }
    
    .telegram-link:active {
        transform: translateY(0);
    }
    
    .telegram-link svg {
        width: 14px;
        height: 14px;
    }
    
    /* Responsive adjustments */
    @media (max-width: 480px) {
        .login-container {
            padding: 1rem;
        }
        
        .card {
            padding: 1.5rem;
        }
        
        .top-logo {
            top: 20px;
            left: 20px;
        }
        
        .time-display {
            top: 20px;
            right: 20px;
        }
        
        .background-text {
            font-size: 30vw;
        }
    }
    
    .password-group {
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s ease;
        max-height: 0;
        overflow: hidden;
    }
    
    .password-group.slide-in {
        opacity: 1;
        transform: translateY(0);
        max-height: 200px;
    }
    
    .error-message {
        color: #ef4444;
        font-size: 0.875rem;
        margin-top: 0.5rem;
    }
</style>