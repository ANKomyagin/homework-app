<script>
	import { onMount } from 'svelte';

	let fullName = $state('');
	let classId = $state(''); 
	let pin = $state('');
	
	let isLoading = $state(false);
	let errorMessage = $state('');
	let schoolClasses = $state([]);

	onMount(async () => {
		try {
			const res = await fetch('/api/classes');
			if (res.ok) {
				schoolClasses = await res.json();
				if (schoolClasses.length > 0) classId = String(schoolClasses[0].id);
			}
		} catch (e) {
			console.error(e);
		}
	});

	async function handleAuth(isRegister) {
		isLoading = true;
		errorMessage = '';
		const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';

		try {
			const res = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ full_name: fullName, class_id: parseInt(classId), pin: pin })
			});

			if (res.ok) {
				if (isRegister) {
					await handleAuth(false);
					return;
				}
				const data = await res.json();
				window.location.href = data.user.role === 'teacher' ? '/teacher' : '/student';
			} else {
				const err = await res.json();
				errorMessage = err.detail || 'Ошибка авторизации';
			}
		} catch (error) {
			errorMessage = 'Ошибка соединения с сервером';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head><title>Вход | Домашние задания</title></svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gray-100 p-4">
	<div class="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 space-y-6">
		<div class="text-center">
			<h1 class="text-3xl font-bold text-gray-900">Сдача ДЗ</h1>
		</div>

		<form class="space-y-4">
			<div>
				<label class="block text-sm font-medium text-gray-700" for="class-select">Класс</label>
				<select id="class-select" bind:value={classId} class="mt-1 block w-full rounded-md border border-gray-300 py-2 px-3 bg-white">
					{#each schoolClasses as sc}
						<option value={String(sc.id)}>{sc.name}</option>
					{/each}
				</select>
			</div>
			<div>
				<label class="block text-sm font-medium text-gray-700" for="fullname-input">Фамилия Имя</label>
				<input id="fullname-input" type="text" bind:value={fullName} placeholder="Иванов Иван" class="mt-1 block w-full rounded-md border border-gray-300 py-2 px-3">
			</div>
			<div>
				<label class="block text-sm font-medium text-gray-700" for="pin-input">ПИН-код (4 цифры)</label>
				<input id="pin-input" type="password" maxlength="4" bind:value={pin} placeholder="••••" class="mt-1 block w-full rounded-md border border-gray-300 py-2 px-3 text-center tracking-[1em] font-bold">
			</div>

			{#if errorMessage} 
				<div class="text-red-600 text-sm text-center bg-red-50 p-2 rounded">{errorMessage}</div> 
			{/if}

			<div class="flex gap-4 pt-2">
				<button type="button" onclick={() => handleAuth(true)} disabled={isLoading} class="w-full py-2.5 bg-gray-200 text-gray-800 rounded-md font-medium hover:bg-gray-300 disabled:opacity-50">Регистрация</button>
				<button type="button" onclick={() => handleAuth(false)} disabled={isLoading} class="w-full py-2.5 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 disabled:opacity-50">Войти</button>
			</div>
			
			<div class="text-center pt-4">
				<a href="/teacher/login" class="text-xs text-gray-400 hover:text-blue-600 transition">
					Вход для преподавателя →
				</a>
			</div>
		</form>
	</div>
</div>
