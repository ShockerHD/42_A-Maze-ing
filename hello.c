/* Day-1 MLX spike: the introduction example from the docs, nothing else.
   Throwaway -- delete once the real renderer opens its own window.

   gcc hello.c -Imlx -Lmlx -lmlx -lXext -lX11 -lXrandr \
       -Wl,-rpath,'$ORIGIN/mlx' -o hello
   ./hello        (Ctrl-C in the terminal to quit -- no hooks yet)
*/

#include "mlx.h"

int	main(void)
{
	void	*mlx;
	void	*mlx_win;

	mlx = mlx_init();
	mlx_win = mlx_new_window(mlx, 1920, 1080, "Hello world!");
	mlx_loop(mlx);
	(void)mlx_win;
	return (0);
}
