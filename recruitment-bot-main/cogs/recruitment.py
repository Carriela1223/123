import asyncio
import datetime
import json
import os

import discord
from discord.ext import interaction

print("recruitment.py 로드됨")

from config.config import get_config
from utils.directory import directory


parser = get_config("config")
comment_parser = get_config("comment")


PENDING_RECRUITMENT_FILE = os.path.join(
    directory,
    "data",
    "pending_recruitment.json",
)


class Recruitment:
    def __init__(
        self,
        client: interaction.Client,
    ):
        self.client = client
        self.color = 0xFFFFFF

        self.has_recruitment_channel = parser.has_option(
            "Default",
            "channels",
        )

        self.recruitment_channel = (
            json.loads(
                parser.get(
                    "Default",
                    "channels",
                )
            )
            if self.has_recruitment_channel
            else []
        )

        self.pending_recruitment = {}
        self.custom_limits = {}

        self.comment_unlimited = comment_parser.get(
            "Recruitment",
            "unlimited",
        )

    # =========================================================
    # 봇 준비
    # =========================================================

    @interaction.listener()
    async def on_ready(
        self,
    ):
        await self.pending_recruitment_init(
            self.load_pending_recruitment()
        )

    # =========================================================
    # 음성채널 정보 포맷
    # =========================================================

    def voice_channel_formatter(
        self,
        regex: str,
        info: discord.VoiceChannel,
    ):
        return regex.format(
            channel_name=info.name,
            channel_id=info.id,
            channel_mention=info.mention,
            category_name=getattr(
                info.category,
                "name",
                "No Category",
            ),
            category_id=getattr(
                info.category,
                "id",
                "No Category Id",
            ),
            category_mention=getattr(
                info.category,
                "mention",
                "No Category",
            ),
            current=f"{len(info.members)}명",
            limit=(
                f"{info.user_limit}명"
                if info.user_limit > 0
                else self.comment_unlimited
            ),
        )

    # =========================================================
    # 모집 저장
    # =========================================================

    def save_pending_recruitment(
        self,
    ):
        data = {}

        for (
            channel_id,
            value,
        ) in self.pending_recruitment.items():

            data[channel_id] = {
                "requester": value["requester"].id,
                "guild": value["guild"].id,
                "channel": value["channel"].id,
                "message": value["message"].id,
                "created_at": value[
                    "created_at"
                ].timestamp(),
            }

        os.makedirs(
            os.path.dirname(
                PENDING_RECRUITMENT_FILE
            ),
            exist_ok=True,
        )

        with open(
            PENDING_RECRUITMENT_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )

    # =========================================================
    # 모집 불러오기
    # =========================================================

    def load_pending_recruitment(
        self,
    ):
        if not os.path.exists(
            PENDING_RECRUITMENT_FILE
        ):
            return []

        try:
            with open(
                PENDING_RECRUITMENT_FILE,
                "r",
                encoding="utf-8",
            ) as file:
                pending = json.load(file)

        except (
            OSError,
            json.JSONDecodeError,
        ):
            return []

        result = []

        for (
            channel_id,
            value,
        ) in pending.items():

            guild = self.client.get_guild(
                value["guild"]
            )

            if guild is None:
                continue

            channel = guild.get_channel(
                value["channel"]
            )

            if channel is None:
                continue

            requester = guild.get_member(
                value["requester"]
            )

            recruitment = {
                "requester": requester,
                "guild": guild,
                "channel": channel,
                "message": channel.get_partial_message(
                    value["message"]
                ),
                "created_at": datetime.datetime.fromtimestamp(
                    value["created_at"],
                    tz=datetime.timezone.utc,
                ),
            }

            self.pending_recruitment[
                str(channel_id)
            ] = recruitment

            result.append(
                {
                    **recruitment,
                    "voice_channel": str(
                        channel_id
                    ),
                }
            )

        return result

    # =========================================================
    # 모집 자동 삭제
    # =========================================================

    async def pending_recruitment_init(
        self,
        pending,
    ):
        if not pending:
            return

        pending.sort(
            key=lambda item: item[
                "created_at"
            ].timestamp()
        )

        while pending:

            item = pending.pop(0)

            now = datetime.datetime.now(
                tz=datetime.timezone.utc
            )

            remain_time = (
                item["created_at"].timestamp()
                + 30
                - now.timestamp()
            )

            if remain_time > 0:
                await asyncio.sleep(
                    remain_time
                )

            try:
                await item[
                    "message"
                ].delete()

            except (
                discord.NotFound,
                discord.Forbidden,
                AttributeError,
            ):
                pass

            self.pending_recruitment.pop(
                item["voice_channel"],
                None,
            )

        self.save_pending_recruitment()

    # =========================================================
    # 음성채널 인원 변경 감지
    # =========================================================

    @interaction.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if before.channel == after.channel:
            return

        for (
            channel_id,
            recruitment,
        ) in list(
            self.pending_recruitment.items()
        ):

            guild = self.client.get_guild(
                recruitment["guild"].id
            )

            if guild is None:
                continue

            voice_channel = guild.get_channel(
                int(channel_id)
            )

            if voice_channel is None:
                continue

            current = len(
                voice_channel.members
            )

            limit = self.custom_limits.get(
                int(channel_id)
            )

            try:
                message = await recruitment[
                    "channel"
                ].fetch_message(
                    recruitment["message"].id
                )

            except (
                discord.NotFound,
                discord.Forbidden,
            ):
                self.pending_recruitment.pop(
                    channel_id,
                    None,
                )

                self.custom_limits.pop(
                    int(channel_id),
                    None,
                )

                self.save_pending_recruitment()

                continue

            # 정원 초과/도달 시 모집글 삭제
            if (
                limit is not None
                and current >= limit
            ):

                try:
                    await message.delete()

                except (
                    discord.NotFound,
                    discord.Forbidden,
                ):
                    pass

                self.pending_recruitment.pop(
                    channel_id,
                    None,
                )

                self.custom_limits.pop(
                    int(channel_id),
                    None,
                )

                self.save_pending_recruitment()

                continue

            if not message.embeds:
                continue

            embed = message.embeds[0]

            embed.title = comment_parser.get(
                "Recruitment",
                "embed_member_count",
            ).format(
                current=f"{current}명",
                limit=f"{limit}명",
            )

            try:
                await message.edit(
                    embeds=[embed]
                )

            except (
                discord.NotFound,
                discord.Forbidden,
            ):
                pass

    # =========================================================
    # /구인
    # =========================================================

    @interaction.command(
        name="구인",
        description="함께 게임을 즐길 파티원을 모집해보세요",
    )
    async def recruitment(
        self,
        ctx: interaction.ApplicationContext,
    ):
        if ctx.guild is None:
            return

        if (
            self.has_recruitment_channel
            and ctx.channel.id
            not in self.recruitment_channel
        ):
            return

        if ctx.author.voice is None:
            await ctx.send(
                comment_parser.get(
                    "Recruitment",
                    "entrance_voice_channel",
                ),
                hidden=True,
            )
            return

        voice_channel = (
            ctx.author.voice.channel
        )

        await ctx.modal(
            custom_id=(
                f"recruitment_"
                f"{ctx.channel.id}_"
                f"{ctx.author.id}_"
                f"{voice_channel.id}"
            ),
            title=comment_parser.get(
                "Recruitment",
                "modal_title",
            ),
            components=[
                interaction.ActionRow(
                    components=[
                        interaction.TextInput(
                            custom_id="custom_limit",
                            style=1,
                            label="모집할 총 인원수 (숫자만 입력)",
                            placeholder="예: 3",
                            required=True,
                        ),
                    ],
                ),
                interaction.ActionRow(
                    components=[
                        interaction.TextInput(
                            custom_id="comment",
                            style=2,
                            label=comment_parser.get(
                                "Recruitment",
                                "modal_description_title",
                            ),
                            placeholder=comment_parser.get(
                                "Recruitment",
                                "modal_description_placeholder",
                            ),
                            required=True,
                        ),
                    ],
                ),
            ],
        )

    # =========================================================
    # 모달 제출
    # =========================================================

    @interaction.listener()
    async def on_modal(
        self,
        ctx: interaction.ModalContext,
    ):
        if (
            not ctx.custom_id.startswith(
                "recruitment"
            )
            or ctx.author.voice is None
        ):
            return

        voice_channel = (
            ctx.author.voice.channel
        )

        user_limit = 4
        user_comment = ""

        for component in ctx.components:

            if component.custom_id == "custom_limit":

                try:
                    user_limit = int(
                        component.value
                    )

                except ValueError:
                    user_limit = 4

            elif component.custom_id == "comment":

                user_comment = (
                    component.value
                )

        self.custom_limits[
            voice_channel.id
        ] = user_limit

        current = len(
            voice_channel.members
        )

        embed = discord.Embed(
            title=comment_parser.get(
                "Recruitment",
                "embed_member_count",
            ).format(
                current=f"{current}명",
                limit=f"{user_limit}명",
            ),
            description=(
                comment_parser.get(
                    "Recruitment",
                    "embed_description",
                ).format(
                    author_mention=ctx.author.mention,
                )
                + f"\n\n💬 **한마디**: {user_comment}"
                + f"\n\n📌 **통화방 위치**: "
                f"{voice_channel.mention}"
            ),
            color=self.color,
        )

        # =====================================================
        # 참가 + 모집 취소 버튼
        # =====================================================

        components = [
            interaction.ActionRow(
                components=[
                    interaction.Button(
                        style=1,
                        custom_id="joinv_button",
                        label=comment_parser.get(
                            "Recruitment",
                            "button",
                        ),
                    ),
                    interaction.Button(
                        style=4,
                        custom_id="cancel_recruitment",
                        label="모집 취소",
                    ),
                ],
            ),
        ]

        message = await ctx.send(
            embed=embed,
            components=components,
        )

        print(
            "버튼 메시지 생성 완료"
        )

        # =====================================================
        # 모집 데이터 저장
        # =====================================================

        self.pending_recruitment[
            str(voice_channel.id)
        ] = {
            "requester": ctx.author,
            "guild": ctx.guild,
            "channel": ctx.channel,
            "voice_channel": voice_channel,
            "message": message,
            "created_at": datetime.datetime.now(
                tz=datetime.timezone.utc
            ),
        }

        self.save_pending_recruitment()

    # =========================================================
    # 참가 버튼
    # =========================================================

    @interaction.detect_component(
        custom_id="joinv_button"
    )
    async def button_test(
        self,
        ctx: interaction.ComponentsContext,
    ):
        print(
            "===== 참가 버튼 클릭 감지 ====="
        )

        if ctx.guild is None:
            await ctx.send(
                "서버에서만 사용할 수 있습니다.",
                hidden=True,
            )
            return

        recruitment = None
        recruitment_key = None

        # 클릭한 모집글 찾기
        for (
            channel_id,
            data,
        ) in self.pending_recruitment.items():

            if (
                data["guild"].id
                == ctx.guild.id
                and data["message"].id
                == ctx.message.id
            ):
                recruitment = data
                recruitment_key = channel_id
                break

        if recruitment is None:
            await ctx.send(
                "현재 진행 중인 모집을 찾을 수 없습니다.",
                hidden=True,
            )
            return

        voice_channel = recruitment.get(
            "voice_channel"
        )

        if voice_channel is None:

            voice_channel = (
                ctx.guild.get_channel(
                    int(recruitment_key)
                )
            )

        if voice_channel is None:
            await ctx.send(
                "모집 음성채널을 찾을 수 없습니다.",
                hidden=True,
            )
            return

        if not isinstance(
            voice_channel,
            discord.VoiceChannel,
        ):
            await ctx.send(
                "모집 채널이 음성채널이 아닙니다.",
                hidden=True,
            )
            return

        member = ctx.guild.get_member(
            ctx.author.id
        )

        if member is None:
            await ctx.send(
                "사용자 정보를 찾을 수 없습니다.",
                hidden=True,
            )
            return

        print(
            "참가 요청자:",
            member.name,
        )

        print(
            "현재 음성채널:",
            (
                member.voice.channel.name
                if member.voice
                and member.voice.channel
                else "없음"
            ),
        )

        print(
            "참가할 음성채널:",
            voice_channel.name,
        )

        # =====================================================
        # 핵심
        #
        # 현재 음성채널이 없어도 이동 가능
        # 다른 음성채널에 있어도 바로 이동 가능
        # =====================================================

        try:

            await member.move_to(
                voice_channel
            )

        except discord.HTTPException as error:

            print(
                "음성채널 이동 실패:",
                error,
            )

            await ctx.send(
                "음성채널로 이동할 수 없습니다.",
                hidden=True,
            )

            return

        print(
            "===== 음성채널 참가 성공 ====="
        )

        await ctx.send(
            (
                f"🔊 {voice_channel.mention}"
                "에 참가했습니다."
            ),
            hidden=True,
        )

    # =========================================================
    # 모집 취소 버튼
    # =========================================================

    @interaction.detect_component(
        custom_id="cancel_recruitment"
    )
    async def cancel_recruitment(
        self,
        ctx: interaction.ComponentsContext,
    ):
        print(
            "===== 모집 취소 버튼 클릭 감지 ====="
        )

        if ctx.guild is None:
            await ctx.send(
                "서버에서만 사용할 수 있습니다.",
                hidden=True,
            )
            return

        recruitment_key = None
        recruitment = None

        # 클릭한 모집글 찾기
        for (
            channel_id,
            data,
        ) in self.pending_recruitment.items():

            if (
                data["guild"].id
                == ctx.guild.id
                and data["message"].id
                == ctx.message.id
            ):
                recruitment_key = channel_id
                recruitment = data
                break

        if recruitment is None:
            await ctx.send(
                "해당 모집글을 찾을 수 없습니다.",
                hidden=True,
            )
            return

        requester = recruitment.get(
            "requester"
        )

        if requester is None:
            await ctx.send(
                "모집 작성자 정보를 찾을 수 없습니다.",
                hidden=True,
            )
            return

        # =====================================================
        # 모집글 작성자만 취소 가능
        # =====================================================

        if ctx.author.id != requester.id:

            await ctx.send(
                "❌ 모집글 작성자만 모집을 취소할 수 있습니다.",
                hidden=True,
            )

            return

        # =====================================================
        # 모집글 삭제
        # =====================================================

        try:

            await recruitment[
                "message"
            ].delete()

        except (
            discord.NotFound,
            discord.Forbidden,
        ):
            pass

        # 메모리에서 제거
        self.pending_recruitment.pop(
            recruitment_key,
            None,
        )

        # 인원 제한 제거
        try:

            self.custom_limits.pop(
                int(recruitment_key),
                None,
            )

        except (
            ValueError,
            TypeError,
        ):
            pass

        # JSON 저장
        self.save_pending_recruitment()

        print(
            "===== 모집 취소 완료 ====="
        )

        await ctx.send(
            "✅ 모집이 취소되었습니다.",
            hidden=True,
        )


# =============================================================
# Cog 등록
# =============================================================

def setup(
    client: interaction.Client,
):
    print(
        "Recruitment Cog 등록"
    )

    client.add_interaction_cog(
        Recruitment(client)
    )