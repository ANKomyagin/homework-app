<script>
	let username = $state('');
	let password = $state('');
	let isLoading = $state(false);
	let errorMessage = $state('');

	async function handleLogin() {
		isLoading = true;
		errorMessage = '';

		try {
			const res = await fetch('/api/auth/teacher/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username, password })
			});

			if (res.ok) {
				window.location.href = '/teacher';
			} else {
				const err = await res.json();
				errorMessage = err.detail || 'Неверный логин или пароль';
			}
		} catch (e) {
			errorMessage = 'Ошибка соединения с сервером';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Вход для учителя</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-slate-900 p-4">
	<div class="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 space-y-6">
		<div class="text-center">
			<h1 class="text-2xl font-bold text-gray-900">Кабинет преподавателя</h1>
			<p class="text-sm text-gray-500 mt-1">Вход для проверки заданий</p>
		</div>

		<form class="space-y-4" onsubmit={(e) => { e.preventDefault(); handleLogin(); }}>
			<div>
				<label class="block text-sm font-medium text-gray-700" for="username">Логин</label>
				<input 
					id="username" 
					type="text" 
					bind:value={username} 
					placeholder="teacher" 
					required
					class="mt-1 block w-full rounded-lg border border-gray-300 py-2.5 px-3 focus:ring-2 focus:ring-slate-800 focus:outline-none"
				>
			</div>

			<div>
				<label class="block text-sm font-medium text-gray-700" for="password">Пароль</label>
				<input 
					id="password" 
					type="password" 
					bind:value={password} 
					placeholder="••••••••" 
					required
					class="mt-1 block w-full rounded-lg border border-gray-300 py-2.5 px-3 focus:ring-2 focus:ring-slate-800 focus:outline-none"
				>
			</div>

			{#if errorMessage}
				<div class="text-red-600 text-sm bg-red-50 p-3 rounded-lg text-center font-medium">
					{errorMessage}
				</div>
			{/if}

			<button 
				type="submit" 
				disabled={isLoading}
				class="w-full py-3 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 transition disabled:opacity-50"
			>
				{isLoading ? 'Проверка...' : 'Войти в панель'}
			</button>

			<div class="text-center pt-2">
				<a href="/" class="text-xs text-gray-500 hover:text-gray-900">← Вернуться к входу для учеников</a>
			</div>
		</form>
	</div>
</div>
