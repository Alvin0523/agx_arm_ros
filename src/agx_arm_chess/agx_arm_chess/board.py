# Measure A1 from /feedback/tcp_pose first!
A1_X = 0.25    # ← replace with your measurement
A1_Y = -0.14   # ← replace with your measurement
BOARD_Z = 0.0  # ← height of board surface
SQUARE_SIZE = 0.045  # 45mm standard chess square

Z_HOVER = 0.15   # safe travel height above board
Z_PICK  = 0.025  # height to grab piece

PIECE_HEIGHT = 0.07   # 7cm tall pieces
PIECE_RADIUS = 0.018  # 18mm radius

def get_square_xy(square_name):
    """e.g. 'e2' -> (x, y)"""
    col = ord(square_name[0]) - ord('a')  # a=0, h=7
    row = int(square_name[1]) - 1         # 1=0, 8=7
    x = A1_X + col * SQUARE_SIZE
    y = A1_Y + row * SQUARE_SIZE
    return x, y

# Initial chess piece positions (standard setup)
INITIAL_PIECES = {
    # White pieces
    'a1': 'white_rook_a1',
    'b1': 'white_knight_b1',
    'c1': 'white_bishop_c1',
    'd1': 'white_queen_d1',
    'e1': 'white_king_e1',
    'f1': 'white_bishop_f1',
    'g1': 'white_knight_g1',
    'h1': 'white_rook_h1',
    'a2': 'white_pawn_a2',
    'b2': 'white_pawn_b2',
    'c2': 'white_pawn_c2',
    'd2': 'white_pawn_d2',
    'e2': 'white_pawn_e2',
    'f2': 'white_pawn_f2',
    'g2': 'white_pawn_g2',
    'h2': 'white_pawn_h2',
    # Black pieces
    'a8': 'black_rook_a8',
    'b8': 'black_knight_b8',
    # ... etc
}