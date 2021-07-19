from cogs.utils import checks, converters, errors, random_text
from cogs.utils.proposal_message_checker import (
    send_proposal_message, TickPayloadCheckResult, ProposalLock, ProposalInProgress, only_mention, escape_markdown,
)
from cogs.utils.customised_tree_user import CustomisedTreeUser
from cogs.utils.family_tree.family_tree_member import FamilyTreeMember
from cogs.utils.family_tree.relationship_string_simplifier import RelationshipStringSimplifier
from cogs.utils.discord_name_manager import DiscordNameManager
from cogs.utils.perks_handler import get_marriagebot_perks, TIER_NONE, TIER_ONE, TIER_TWO, TIER_THREE, TIER_VOTER, MarriageBotPerks
from cogs.utils.time_handler import fix_time_string


def get_family_guild_id(ctx) -> int:
    if ctx.bot.config['is_server_specific']:
        return ctx.guild.id
    return 0


def guild_allows_incest(ctx) -> bool:
    if get_family_guild_id(ctx) == 0:
        return False
    return ctx.bot.guild_settings[ctx.guild.id]['allow_incest']


def get_max_family_members(ctx) -> int:
    if get_family_guild_id(ctx) == 0:
        return ctx.bot.config['max_family_members']
    return ctx.bot.guild_settings[ctx.guild.id]['max_family_members']
