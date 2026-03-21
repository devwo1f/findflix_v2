import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/app_colors.dart';
import '../models/title_model.dart';
import 'rating_widget.dart';
import 'shimmer_loading.dart';

/// Compact title card for grids and horizontal lists.
class TitleCard extends StatelessWidget {
  final TitleModel title;
  final double width;
  final double height;
  final bool showRating;
  final bool showYear;

  const TitleCard({
    super.key,
    required this.title,
    this.width = 140,
    this.height = 210,
    this.showRating = true,
    this.showYear = true,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => context.push('/title/${title.id}'),
      child: SizedBox(
        width: width,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Poster
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: SizedBox(
                width: width,
                height: height,
                child: title.posterUrl != null
                    ? CachedNetworkImage(
                        imageUrl: title.posterUrl!,
                        fit: BoxFit.cover,
                        placeholder: (_, __) => ShimmerLoading(
                          height: height,
                          width: width,
                          borderRadius: 12,
                        ),
                        errorWidget: (_, __, ___) => _posterFallback(),
                      )
                    : _posterFallback(),
              ),
            ),
            const SizedBox(height: 8),
            // Title
            Text(
              title.title,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 2),
            // Meta row
            Row(
              children: [
                if (showYear && title.year.isNotEmpty) ...[
                  Text(
                    title.year,
                    style: const TextStyle(
                      color: AppColors.textTertiary,
                      fontSize: 11,
                    ),
                  ),
                ],
                if (showRating && title.voteAverage > 0) ...[
                  if (showYear && title.year.isNotEmpty)
                    const SizedBox(width: 6),
                  const Icon(
                    Icons.star_rounded,
                    size: 12,
                    color: AppColors.ratingGold,
                  ),
                  const SizedBox(width: 2),
                  Text(
                    title.ratingFormatted,
                    style: const TextStyle(
                      color: AppColors.ratingGold,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _posterFallback() {
    return Container(
      color: AppColors.card,
      child: Center(
        child: Icon(
          title.type == 'tv' ? Icons.tv_rounded : Icons.movie_rounded,
          color: AppColors.textTertiary,
          size: 40,
        ),
      ),
    );
  }
}

/// Horizontal scrollable list of title cards.
class TitleCardList extends StatelessWidget {
  final List<TitleModel> titles;
  final double cardWidth;
  final double cardHeight;

  const TitleCardList({
    super.key,
    required this.titles,
    this.cardWidth = 130,
    this.cardHeight = 195,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: cardHeight + 48,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: titles.length,
        separatorBuilder: (_, __) => const SizedBox(width: 12),
        itemBuilder: (_, index) => TitleCard(
          title: titles[index],
          width: cardWidth,
          height: cardHeight,
        ),
      ),
    );
  }
}
